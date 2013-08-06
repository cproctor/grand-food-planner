# Import the other libraries we need.
import csv
import re
import os
import inspect

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

class FoodPlannerModel(object):

    # The initialization function. By the end of __init__, the 
    # model should be ready to be used by a view
    def __init__(self, ingredients=None, menus=None, purchases=None, 
            verbose=False):
        self.verbose = verbose
        self.settings = {
            "ingredients"   : ingredients,
            "menus"         : menus,
            "purchases"     : purchases
        }
        self.storageLocations = STORAGE_LOCATIONS

        #self.ingredients = self.generate_ingredients()
        #self.menuItems = self.generate_menu_items()
        #self.purchases = self.read_file(self.settings['purchases'])

    def get_buy_list(self):
        "Generate the data for a buy list"

        # This is fake data!
        return {
            "stores": [
                {
                    'name': 'Seven-Eleven',
                    'items': [
                        {
                            'quantity': 7,
                            'unit': 'gallons',
                            'name': 'Slurpee',
                            'buyNotes': 'Mix Dr. Pepper with Cherry'
                        },
                        {
                            'quantity': 12,
                            'unit': 'bags',
                            'name': 'Corn nuts',
                            'buyNotes': ''
                        }
                    ]
                },
                {
                    'name': 'JJ&F',
                    'items': [
                        {
                            'quantity': 2,
                            'unit': 'cups',
                            'name': 'Fancy mustard',
                            'buyNotes': 'mmm'
                        },
                        {
                            'quantity': 2,
                            'unit': 'oz',
                            'name': 'Raw fish',
                            'buyNotes': 'keep it clean'
                        }
                    ]
                }

            ]
        }

    # Do all the work required to get a valid list of ingredients. 
    # If we're in strict mode, then kill the program if there are errors.
    def generate_ingredients(self, strict=True):

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
            'buyStoreAlternate' : 'None',
            'notes'             : ''
        }

        for eachIngredient in ingredients:
            # Use the is_empty helper method to see whether this was a blank
            # If so, we call continue, which skips the rest of this loop 
            # iteration and starts with the next eachIngredient
            if self.is_empty(eachIngredient):
                continue

            # Set default values so we'll always have some value in place 
            # for each property of an ingredient.
            eachIngredient = self.set_defaults(eachIngredient, defaults)

            # Now we have to check whether there's a name and a buyStore,
            # the minimum requirements for an ingredient. If there is, 
            # add it to our result list.
            if self.has_properties(eachIngredient, requiredProperties):
                result.append(eachIngredient)
            # If not, make a note in errors
            else:
                errors.append("Invalid ingredient: %s" % eachIngredient)

        # If we're in strict mode, things should fail if there are errors.
        # In this case, we'll raise a ValueError, and give it an explanation
        # of what went wrong. We use '\n'.join(errors) to convert the list
        # of errors into a string with a \n, the newline character, between each
        if strict and any(errors):
            raise ValueError("Invalid ingredients:\n" + '\n'.join(errors))

        # If we weren't strict, or there weren't any errors, we succeeded, so 
        # we can return result, which is the list of valid ingredients. Just for
        # fun, we'll sort them in alphabetical order.
        return sorted(result, key='name')

    # Generate the menu items. This will follow much the same pattern as
    # generate_ingredients. 
    def generate_menu_items(self):

        # Get the raw data, and create lists for the result and the errors
        menuItems = self.read_file(self.settings['menus'])
        result = []
        errors = []

        # We'll define a list of properties we require for each menu item
        requiredProperties = [
            'day',
            'meal',
            'mealType',
            'dish',
            'item',
            'quantity'
        ]

        defaults = {
            'cookingNotes': '',
            'buyingNotes': ''
        }

        # A helper function that returns the storage location of a menu item
        def get_storage_location(menuItem):
            # Go through each storage location and see if this menuItem
            # is stored there.
            for location in self.storageLocations:
                if menuItem.get(location, False):
                    return location
            # If we didn't find a match...
            return "NO STORAGE LOCATION"

        # Work with the menuItems one at a time...
        for eachMenuItem in menuItems:

            # Again, skip the blanks
            if self.is_empty(eachMenuItem):
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
                    eachMenuItem['storage'] = get_storage_location(eachMenuItem)

                    # And add this menu item to the list of good ones
                    result.append(eachMenuItem)

                else:
                    errors.append("Invalid menu item: there is no ingredient named %s" % 
                            eachMenuItem['item'])
            else:
                errors.append("Invalid menu item: missing properties: %s" % eachMenuItem)

        # If we're in strict mode, things should fail if there are errors.
        # In this case, we'll raise a ValueError, and give it an explanation
        # of what went wrong. We use '\n'.join(errors) to convert the list
        # of errors into a string with a \n, the newline character, between each
        if strict and any(errors):
            raise ValueError("Invalid menu items:\n" + '\n'.join(errors))

        # If we weren't strict, or there weren't any errors, we succeeded, so 
        # we can return result, which is the list of valid menu items.
        return result



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
            # to skip some number of rows, so we'll call reader.read() without 
            # capturing the data some number of times.
            for eachRowToSkip in range(fileSettings['rowsToSkip']):
                reader.read()

            # Now we'll convert the rest of the rows available into a list, so 
            # we can let the reader release the file and still have a copy of
            # the data. We'll return that list.
            return [row for row in reader]

    def has_properties(self, dictToTest, properties):
        "Check whether a dict has certain properties defined"
    
        # Go through each required property and make sure the dict has it.
        # If not, return False
        for prop in properties:
            if not dictToTest.get(prop):
                return False

        # The dict had all the properties. Return True.
        return True

    def set_defaults(self, dictToUpdate, defaults):
        "Return a dict with defaults set"
        
        # It's necessary to create a copy of the dict--otherwise, we would
        # actually change the dict that got passed in. It's surprising to 
        # have a function mess with values you pass in, and in programming,
        # surprises are bad. Don't expect yourself to fully get why this is 
        # necessary yet.
        newDict = dict(defaults)

        # Overwrite each property in newDict with the properties in dictToUpdate
        # Effectively, this means the only default settings remaining will be
        # those that aren't set in dictToUpdate
        newDict.update(dictToUpdate)
        
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


# ===============================================================================
# THESE WERE OLD METHODS THAT PERTAINED TO THE MODEL. WE MAY OR MAY NOT NEED THEM
# ===============================================================================

    def ingredients(self):
        ingredients = set([entry.get('item') for entry in self.data])
        #print "We are using the following ingredients on our trip"
        #for i in sorted(ingredients, key=str.lower):
        #    print "  * %s" % i
        ingredients = [i.strip() for i in ingredients]
        return ingredients
    
    # this function creates a dict of storage locations pair with lists of ingredients to
    # be stored in those locations
    def sort_ingred_by_storage(self):
        # For each storage location make a list with all items that are associated with it
        # To create the desired dict, we are making the empty dict variable ingredientsByStorageLocation to be filled later
        ingredientsByStorageLocation = {}
        # The below function creates a single list of ingredients associated with a particular location
        def ingredients_in_location(location):
            #print "I have no idea what's going on, but somebody wants to find the ingredients in %s" % location
            ingredientsInLocation = []
            # For given storage location, list ingredients stored here.
            for eachEntry in self.data:
                # Here we are checking if the particular location we're comparing to for this
                # iteration of this bit of code is equivalent to the location of the 
                # item in the spreadsheet
                # Trouble! eachItem doesn't have a storage property. Let's see what is there...
                if location == eachEntry['storage']:
                    ingredientsInLocation.append(eachEntry)
            #print "The ingredients in %s are %s" % (location, ', '.join(sorted(ingredientsInLocation)))
            def prepareForComparison(entry):
                return entry['item']
            return sorted(ingredientsInLocation, key=prepareForComparison)
        # In this for loop, we create a local variable called eachStorageLocation
        # into which we iteratively pass values from self.storageLocations
        for eachStorageLocation in self.storageLocations:
            # The following syntax allows us to assign values to keys within the dict we 
            # are ultimately creating
            #print "I am currently working with %s" % eachStorageLocation   
            ingredientsByStorageLocation[eachStorageLocation] = ingredients_in_location(eachStorageLocation)
        return ingredientsByStorageLocation
    
    def get_stores(self):
        storeNames = set([entry.get('buyStore') for entry in self.data])
        return [{"name":eachStoreName} for eachStoreName in storeNames] 

    # As in SpreadsheetLoader, this method handles the logic around whether and
    # how to report messages.
    def log(self, message):
        "Log a message"
        if self.verbose:
            print message
