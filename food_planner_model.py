# Import the other libraries we need.
import csv
import re
import os
import inspect
import time
from pprint import pprint as p
from datetime import datetime

STORAGE_LOCATIONS = [
    'inCoolerFrozen',
    'inCoolerCool',
    'inBoxVeg',
    'inBoxFruit',
    'inBoxDry',
    'inBoxBread',
    'inBoxOther',
    'inCondiments'
]

NOW = datetime.now().strftime('%A %B %d, %Y at %I:%M %p')

class FoodPlannerModel(object):

    # The initialization function. By the end of __init__, the 
    # model should be ready to be used by a view
    def __init__(self, ingredients=None, menus=None, purchases=None, 
            verbose=False, strict=False, warnings=False):
        self.verbose = verbose
        self.strict = strict
        self.showWarnings = warnings or verbose
        self.settings = {
            "ingredients"   : ingredients,
            "menus"         : menus,
            "purchases"     : purchases
        }
        self.storageLocations = STORAGE_LOCATIONS

        self.ingredients = self.generate_ingredients()
        self.menuItems = self.generate_menu_items()
        self.purchases = self.generate_purchases()

    def get_buy_list(self):
        "Generate the data for a buy list"
        records = []
        # Get a list of all unique combinations of name and unit
        for record in self.purchases + self.menuItems:
            if not any([r for r in records if r['name'] == record['name'] and r['unit'] == record['unit']]):
                records.append({
                    'name': record.get('name', record.get('item')),
                    'unit': record['unit'],
                    'store': self.get_ingredient_store(record['name'])
                })

        stores = []
        for store in self.store_names():
            storeRecords = [r for r in records if r['store'] == store]
            ingredientsFromStore = []
            for record in storeRecords:
                required = self.get_quantity_required(record['name'], record['unit'])
                purchased = self.get_quantity_purchased(record['name'], record['unit'])
                ingredientsFromStore.append({
                    'name': record['name'],
                    'unit': record['unit'],
                    'quantityRequired': required,
                    'quantityPurchased': purchased,
                    'quantityStillNeeded': required - purchased,
                    'notes': '; '.join(self.get_notes(record['name'], menu_cook=False))
                })
            ingredientsFromStore = sorted(ingredientsFromStore, key=lambda i: i['name'])
            
            stores.append({
                'name': store,
                'ingredients': ingredientsFromStore
            })

        return {"stores": stores, "time": NOW}

            
    def get_pack_list(self):
        records = []
        # Get a list of all unique combinations of name and unit
        for record in self.menuItems:
            if not any([r for r in records if r['name'] == record['name'] and r['unit'] == record['unit']]):
                records.append({
                    'name': record['name'],
                    'unit': record['unit'],
                    'quantity': self.get_quantity_required(record['name'], record['unit']),
                    'container': self.get_storage_container(record),
                    'notes': '; '.join(self.get_notes(record['name'], menu_cook=False))
                })
        for record in self.purchases:
            if not any([r for r in records if r['name'] == record['name'] and r['unit'] == record['unit']]):
                records.append({
                    'name': record['name'],
                    'unit': record['unit'],
                    'quantity': self.get_quantity_required(record['name'], record['unit']),
                    'container': self.get_storage_container(self.get_menu_item(record) or
                            {'storage': 'NO STORAGE LOCATION'}),
                    'notes': '; '.join(self.get_notes(record['name'], menu_cook=False))
                })
        records = sorted(records, key=lambda r: r['name'])

        containerList = list(set([i['container'] for i in records]))
        containers = []
        for container in containerList:
            containerRecords = filter(lambda r: r['container'] == container, records)

            containers.append({
                'itemList': containerRecords,
                'name': container
            })
        return {"containers": sorted(containers, key=lambda i: i['name']), "time": NOW}

    def get_menu_item(self, purchase):
        "Find a matching menu item for a purchase"
        for menuItem in self.menuItems:
            if ((purchase['name'] == menuItem['name']) and
                (purchase['day'] == menuItem['day'] or not purchase['day']) and
                (purchase['meal'] == menuItem['meal'] or not purchase['meal'])):
                return menuItem
        self.warn_or_crash("Can't find a menu item matching purchase %s" % purchase)

    def get_cook_list(self):
        cookList = []
        mealNames = {
            '1B': 'Breakfast',
            '2L': 'Lunch',
            '3D': 'Dinner'
        }
        for meal in self.meals():
            ingredients = self.ingredients_for(meal['day'], meal['meal'])
            for ingredient in ingredients:
                ingredient['notes'] = '; '.join(self.get_notes(ingredient['name']))
                ingredient['container'] = self.get_storage_container(ingredient)
            def compareIngredients(a, b):
                if a['container'] != b['container']:
                    return 1 if a['container'] > b['container'] else -1
                elif a['name'] != b['name']:
                    return 1 if a['name'] > b['name'] else -1
                else:
                    return 0
            ingredients = sorted(ingredients, compareIngredients) 
            cookList.append({
                'day': meal['day'],
                'name': mealNames[meal['meal']],
                'ingredients': ingredients
            })
        return {'meals': cookList, 'time': NOW}

    def meals(self):
        mealList = []
        for item in self.menuItems:
            itemMeal = {
                'day': item['day'],
                'meal': item['meal']
            }
            if not itemMeal in mealList and itemMeal['day'] and itemMeal['meal']:
                mealList.append(itemMeal)
        return sorted(mealList, key=lambda m: int(m['day']) * 100 + int(m['meal'][0]))

    def ingredients_for(self, day, meal):
        ingredients = [i for i in self.menuItems if i['day'] == day and i['meal'] == meal]
        return sorted(ingredients, key=lambda i: i['name'])
            
    # Do all the work required to get a valid list of ingredients. 
    # If we're in strict mode, then kill the program if there are errors.
    def generate_ingredients(self):
        self.log("GENERATING INGREDIENTS")

        # We'll start with the raw data.
        ingredients = self.read_file(self.settings['ingredients'])
    
        # We're going to need a list to keep track of the valid 
        # ingredients, and another to keep track of any errors.
        result = []
        errors = []

        # We list the required properties for each ingredient.
        requiredProperties = ['name', 'buyStore']

        # The default values, in case a property is not set
        defaults = {
            # NOTE: We decided that when there's no buyStore, we'll fake
            # it for now.
            'buyStore'          : 'NO STORE DEFINED',
            'buyStoreAlternate' : 'None',
            'notes'             : ''
        }

        for eachIngredient in ingredients:

            # Strip off whitespace from all strings, so that 'pickles' matches 
            # 'pickles '
            self.strip_strings_in_dict(eachIngredient)

            # Use the is_empty helper method to see whether this was a blank
            # If so, we call continue, which skips the rest of this loop 
            # iteration and starts with the next eachIngredient
            if self.is_empty(eachIngredient) or not eachIngredient['name']:
                self.log("skipping empty row: %s" % eachIngredient)
                continue

            # Set default values so we'll always have some value in place 
            # for each property of an ingredient.
            eachIngredient = self.set_defaults(eachIngredient, defaults)

            result.append(eachIngredient)

            # NOTE: Changed the flow here--no longer checking for required
            # properties. Instead, we're going to just go with it.
            # Now we have to check whether there's a name and a buyStore,
            # the minimum requirements for an ingredient. If there is, 
            # add it to our result list.
            #if self.has_properties(eachIngredient, requiredProperties):
                #result.append(eachIngredient)
            # If not, make a note in errors
            #else:
                #errors.append("Invalid ingredient: %s" % eachIngredient)

        # If we're in strict mode, things should fail if there are errors.
        # In this case, we'll raise a ValueError, and give it an explanation
        # of what went wrong. We use '\n'.join(errors) to convert the list
        # of errors into a string with a \n, the newline character, between each
        if any(errors):
            error = "Invalid ingredients:\n" + '\n'.join(errors)
            if self.strict:
                raise ValueError(error)
            else:
                self.warn(error)

        ingredientNames = [i['name'] for i in result]
        similarNames = self.check_for_similar_strings(ingredientNames)
        if any(similarNames):
            errorList =  ["Found similar ingredient names:"]
            for firstString, secondString in similarNames:
                errorList.append("  * '%s' is similar to '%s'" % 
                        (firstString, secondString))
            self.warn_or_crash('\n'.join(errorList))

        duplicates = self.check_for_duplicates(ingredientNames)
        if any(duplicates):
            errorList = ["Found duplicates in ingredients:"]
            for dup in duplicates:
                errorList.append("  * %s" % dup)
            self.warn_or_crash('\n'.join(errorList))

        # If we weren't strict, or there weren't any errors, we succeeded, so 
        # we can return result, which is the list of valid ingredients. Just for
        # fun, we'll sort them in alphabetical order.
        #return sorted(result, key='name')
        return result

    # Generate the menu items. This will follow much the same pattern as
    # generate_ingredients. 
    def generate_menu_items(self):
        self.log("GENERATING MENU ITEMS")

        # Get the raw data, and create lists for the result and the errors
        menuItems = self.read_file(self.settings['menus'])
        result = []
        errors = []

        # We'll define a list of properties we require for each menu item
        requiredProperties = [
            'day',
            'meal',
            #'mealType',
            #'dish',
            'item',
            'quantity'
        ]

        defaults = {
            'cookingNotes': '',
            'buyingNotes': ''
        }

        # Work with the menuItems one at a time...
        for eachMenuItem in menuItems:

            # Strip off whitespace from all strings, so that 'pickles' matches 
            # 'pickles '
            self.strip_strings_in_dict(eachMenuItem)

            # Again, skip the blanks--or anything without an item name
            if self.is_empty(eachMenuItem) or not eachMenuItem['item']:
                self.log("skipping empty row: %s" % eachMenuItem)
                continue

            # Check whether it has the required properties
            if self.has_properties(eachMenuItem, requiredProperties):
            
                # Look up this ingredient in the ingredients list to get its 
                # data. If the lookup was successful, then we can add this
                # menuItem to the list of valid menuItems
                if self.get_ingredient(eachMenuItem['item']):
    
                    # Now that we know we're going to use this one, set its
                    # defaults, its ingredient data, and its storage location
                    eachMenuItem = self.set_defaults(eachMenuItem, defaults)
                    eachMenuItem = self.set_ingredient_data(eachMenuItem, eachMenuItem['item'])
                    eachMenuItem['storage'] = self.get_storage_location(eachMenuItem)

                    # parse the quantity string
                    parsedQuantity = self.parse_quantity_string(str(eachMenuItem['quantity']))
                    self.log("parsing '%s' as '%s' of unit '%s' (using parse method %s)" % (str(eachMenuItem['quantity']), parsedQuantity['quantity'], parsedQuantity['unit'], parsedQuantity['parseMethod']))
            
                    # Update selectively overwrites a dict's values with another 
                    # dict's values. Here, parsedQuantity contains 'quantity' and 
                    # 'unit'
                    eachMenuItem.update(parsedQuantity)

                    # And add this menu item to the list of good ones
                    result.append(eachMenuItem)

                else:
                    errors.append("Skipping invalid menu item '%s': there is no ingredient named %s" % 
                            (eachMenuItem['item'], eachMenuItem['item']))
            else:
                errors.append("Skipping invalid menu item %s: missing properties: %s" % 
                        (eachMenuItem['item'], eachMenuItem))

        # If we're in strict mode, things should fail if there are errors.
        # In this case, we'll raise a ValueError, and give it an explanation
        # of what went wrong. We use '\n'.join(errors) to convert the list
        # of errors into a string with a \n, the newline character, between each
        if any(errors):
            error = "Invalid menu items:\n" + '\n'.join(["  * %s" % e for e in errors])
            if self.strict:
                raise ValueError(error)
            else: 
                self.warn(error)

        # If we weren't strict, or there weren't any errors, we succeeded, so 
        # we can return result, which is the list of valid menu items.
        return result

    def generate_purchases(self):
        purchases = self.read_file(self.settings['purchases'])
        goodPurchases = []
        for purchase in purchases:
            if not purchase['unit']:
                purchase['unit'] = 'count'
            if not purchase['unitsPerCount']:
                purchase['unitsPerCount'] = 1
            purchase['name'] = purchase['name'].lower()
            purchase['count'] = float(purchase['count'])
            purchase['unitsPerCount'] = float(purchase['unitsPerCount'])
            purchase['unit'] = purchase['unit'].strip().strip('.')
            if self.get_ingredient(purchase['name']):
                goodPurchases.append(purchase)
            else:
                self.warn_or_crash("Skipping invalid purchase: there is no ingredient named %s" % purchase['name'])
        return goodPurchases


    # ===============
    # Helpers
    # ===============

    # We use read_file to read each of the three csv files 
    def read_file(self, fileSettings):
        "Read in a csv file and return a list of the data it contains"

        # Let 'em know what's going on.
        self.log("Attempting to read in %s, skipping the first %s rows" % 
                (fileSettings['file'], fileSettings['rowsToSkip']))

        # We create a csv reader which will return a dict for each row it reads
        with open(fileSettings['file']) as csvFile:
            reader = csv.DictReader(csvFile, fileSettings['fieldNames'])

            # The reader has a 'cursor' pointing to the place in the file it's 
            # currently reading from. Every time we call read, it moves the cursor 
            # forward. (You could call reader.rewind() if you wanted). But we want
            # to skip some number of rows, so we'll call reader.next() without 
            # capturing the data some number of times.
            for eachRowToSkip in range(fileSettings['rowsToSkip']):
                self.log("Skipping header row: %s" % reader.next())

            # Now we'll convert the rest of the rows available into a list, so 
            # we can let the reader release the file and still have a copy of
            # the data. We'll return that list.
            return [row for row in reader]

    def has_properties(self, dictToTest, properties):
        "Check whether a dict has certain properties defined"
        return not any(self.missing_properties(dictToTest, properties))

    def missing_properties(self, dictToTest, properties):
        "Returns a list of properties missing from a dict"
        # Go through each required property and make sure the dict has it.
        # If not, add this prop to missing.
        missing = []
        for prop in properties:
            if dictToTest.get(prop, None) is None:
                missing.append(prop)
        return missing

    def set_defaults(self, dictToUpdate, defaults):
        "Return a dict with defaults set"
        
        newDict = dict(dictToUpdate)

        # Overwrite each property in newDict with the properties in dictToUpdate
        # Effectively, this means the only default settings remaining will be
        # those that aren't set in dictToUpdate
        for key, value in defaults.iteritems():
            if not newDict.get(key):
                newDict[key] = value
        
        return newDict

    def set_ingredient_data(self, dictToUpdate, ingredientName):
        "Update a dict with ingredient data"
        # As with the previous method, we want to work with a copy of the 
        # dict that was passed in
        newDict = dict(dictToUpdate)
        
        # Update--overwrite selected properties--of newDict with the ingredient
        # data
        newDict.update(self.get_ingredient(ingredientName))
        return newDict

    def is_empty(self, dictToTest):
        "Check whether a dict is empty"
        
        # Get a set of the unique values in the dictionary. 
        # (A dictionary maps keys to values. When you call values(), you get a 
        # list of just the values.)
        values = set(dictToTest.values())

        # One of two conditions makes the dictionary empty:
        #  1. There are no keys or values: {}
        #  2. All the values are falsy (such as None or the empty string)
        # The function returns true if either of these is true.
        return len(values) == 0 or len(values) == 1 and not list(values)[0]

    # Gets an ingredient by name from the ingredients list. This can also be 
    # used to check whether an ingredient is in the list, since we'll get a
    # truthy dict if there is one, and we'll get False if the name doesn't match
    def get_ingredient(self, itemName):
        "Look up an ingredient by name, returning False if it's not here"

        # This method only works if we've already got our list of ingredients.
        # If you try to use this method before that's done, we have a problem.
        if not self.ingredients:
            raise Exception("The ingredients list has not yet been generated")

        # Create a list of matching ingredients. This line can be read as:
        #   "Create a list for me: Take each ingredient from self.ingredients
        #   and put it in the list if its name matches itemName."
        # This list, which we'll call 'matches', should have zero or one items.
        matches = [ing for ing in self.ingredients if ing['name'] == itemName]

        # Check how many items are in matches. If there's one, return it. 
        if any(matches):
            return matches[0]
        # Otherwise, return False
        else:
            return False

    def store_names(self):
        "Return a list of all store names"
        return sorted(list(set([i['buyStore'] for i in self.ingredients])))

    def ingredient_names(self):
        "Return a list of ingredient names"
        return sorted([i['name'] for i in self.ingredients])

    def menu_item_totals(self):
        "Return a list of menu items, where items of the same name are joined"
        itemTotals = []
        for eachIngredient in self.ingredients:
            ingredientUses = [i for i in self.menuItems if i['name'] == eachIngredient['name']]
            ingredientUnits = list(set([i['unit'] for i in ingredientUses]))
            for ingredientUnit in ingredientUnits:
                ingredientUsesWithUnit = [i for i in ingredientUses if i['unit'] == ingredientUnit]
                if any(ingredientUsesWithUnit):
                    totalQuantity = sum([i['quantity'] for i in ingredientUsesWithUnit])
                    buyNotes = filter(lambda i: i, [i['notes'] for i in ingredientUsesWithUnit])
                    buyNotes.append(eachIngredient['notes'])
                    ingredientTotal = ingredientUses[0]
                    ingredientTotal.update({
                        'quantity': totalQuantity,
                        'buyNotes': '; '.join(buyNotes)
                    })
                    itemTotals.append(ingredientTotal)
        return itemTotals

    def parse_quantity_string(self, quantityString):
        numericalQuantity = "^\s*~?(\d+(\.\d+)?)\s*(.+)$"
        fractionalQuantity = "^\s*~?(\d+)\s*/\s*(\d+)\s*(.+)$"
        noUnitQuantity = "^\s*~?(\d+(\.\d+)?)\s*$"

        # ex: 16
        result = re.match(noUnitQuantity, quantityString)
        if result:
            return {
                'quantity': float(result.group(1)),
                'unit': 'count',
                'parseMethod': 'noUnitQuantity'
            }

        # ex: 3/4 cup
        result = re.match(fractionalQuantity, quantityString)
        if result:
            return {
                'quantity': float(result.group(1)) / int(result.group(2)),
                'unit': result.group(3).strip(),
                'parseMethod': 'fractionalQuantity'
            }
    
        # ex: 12 pounds
        result = re.match(numericalQuantity, quantityString)
        if result:
            return {
                'quantity': float(result.group(1)),
                'unit': result.group(3).strip(),
                'parseMethod': 'numericalQuantity'
            }

        # ex: dozen
        if len(quantityString.strip()) > 0:
            return {
                'quantity': 1,
                'unit': quantityString.strip(),
                'parseMethod': 'unitNoQuantity'
            }

        # it's blank
        else:
            return {
                'quantity': 1,
                'unit': 'count',
                'parseMethod': 'blankOneCount'
            }

    def check_for_similar_strings(self, strings):
        "Compare each string against each other. This is slow."
        similarStrings = []
        for firstString in strings:
            for secondString in strings:
                if firstString in secondString and firstString != secondString:
                    similarStrings.append([firstString, secondString])
        return similarStrings

    def check_for_duplicates(self, strings):
        uniques = []
        duplicates = []
        for string in strings:
            if string in uniques:
                duplicates.append(string)
            else:
                uniques.append(string)
        return duplicates

    def strip_strings_in_dict(self, dictToStrip):
        stringKeys = [key for key, val in dictToStrip.iteritems() if isinstance(val, basestring)]
        for key in stringKeys:
            dictToStrip[key] = dictToStrip[key].strip()


    # As in SpreadsheetLoader, this method handles the logic around whether and
    # how to report messages.
    def log(self, message):
        "Log a message"
        if self.verbose:
            print "INFO " + message

    def warn(self, warning):
        if self.showWarnings:
            print "WARN " + warning

    def warn_or_crash(self, warning):
        if self.strict:
            raise ValueError(warning)
        else:
            self.warn(warning)

    # A helper function that returns the storage location of a menu item
    def get_storage_location(self, menuItem):
        # Go through each storage location and see if this menuItem
        # is stored there.
        for location in self.storageLocations:
            if menuItem.get(location, False):
                return location
        # If we didn't find a match...
        return "NO STORAGE LOCATION"

    def get_quantity_purchased(self, itemName, unit):
        quantityPurchased = 0
        for purchase in self.purchases:
            if purchase['name'] == itemName and purchase['unit'] == unit:
                quantityPurchased += purchase['count'] * purchase['unitsPerCount']
        return quantityPurchased

    def get_quantity_required(self, itemName, unit):
        quantityPurchased = 0
        for requirement in self.menuItems:
            if requirement['name'] == itemName and requirement['unit'] == unit:
                quantityPurchased += requirement['quantity']
        return quantityPurchased


    def get_ingredient_store(self, name):
        for ingredient in self.ingredients:
            if ingredient['name'] == name:
                return ingredient['buyStore']

    def get_ingredient_notes(self, name):
        return filter(None, [self.get_ingredient(name)['notes']])

    def get_menu_buy_notes(self, name, label=True):
        return self._get_menu_notes(name, 'buyingNotes', label=label)

    def get_menu_cook_notes(self, name, label=True):
        return self._get_menu_notes(name, 'cookingNotes', label=label)

    def get_purchase_notes(self, name, label=True):
        purchaseNotes = []
        for purchase in self.purchases:
            if purchase['name'] == name:
                labelString = self._note_label('Purchase', purchase, label)
                if purchase['notes']:
                    purchaseNotes.append(labelString + purchase['notes'])
                if purchase['description']:
                    purchaseNotes.append(
                        labelString + 
                        ("%(description)s was bought on %(shoppingTrip)s" %
                        purchase)
                    )
        return purchaseNotes

    def get_notes(self, name, ingredient=True, menu_buy=True, menu_cook=True, 
            purchase=True, label=True):
        return ([] + 
            (self.get_ingredient_notes(name) if ingredient else []) + 
            (self.get_menu_buy_notes(name, label=label) if menu_buy else []) + 
            (self.get_menu_cook_notes(name, label=label) if menu_cook else []) + 
            (self.get_purchase_notes(name, label=label) if purchase else []))

    def _get_menu_notes(self, name, prop, label=True):
        return [self._note_label('Menu', i, label) + i[prop] for i in 
                self.menuItems if i['name'] == name and i[prop]]

    def _note_label(self, prefix, item, labelWanted):
        if labelWanted:
            labelList = [prefix, item.get('day', ''), (item.get('meal') or ['',''])[1]]
            return '[%s] ' % ' '.join(filter(None, labelList))
        else:
            return ''

    def get_storage_container(self, menuItem):
        storage = menuItem['storage']

        if storage == 'NO STORAGE LOCATION':
            return 'NO STORAGE LOCATION'

        if storage == 'inCondiments':
            return 'condiments box'

        if storage == 'inBoxSnacks':
            return 'snacks box'

        if menuItem['meal'] in ['1B', '2L']:
            bagNumber = int(menuItem['day'] or 0) - 1
        else:
            bagNumber = int(menuItem['day'] or -1)
        containerNumber = (bagNumber / 5) + 1
        if bagNumber == -1:
            return "NO STORAGE LOCATION"

        if 'inBox' in storage:
            container = 'drybox'
        if 'inCooler' in storage:
            container = 'cooler'

        return 'bag %s in %s %s' % (bagNumber, container, containerNumber)

    def get_time(self):
        return {'time': NOW}
