#! /usr/bin/python
import csv
import re
from jinja2 import Environment, FileSystemLoader
import shutil
import os
import inspect
# A little trick. Now I can call p(valueIwantToPrint) and see it nicely
from pprint import pprint as p
env = Environment(loader=FileSystemLoader('Templates'))

BUILD_TARGET = '_build'

class FoodPlanner(object):

    def __init__(self, csvFileName, fieldNames, skipRows=0):
        with open(csvFileName) as csvFile:
            reader = csv.DictReader(csvFile, fieldNames)
            for badRow in range(skipRows or 0):
                reader.read()
            self.data = [row for row in reader]
        self.storageLocations = [
            'inCoolerFrozen',
            'inCoolerCool',
            'inBoxVeg',
            'inBoxFruit',
            'inBoxDry',
            'inBoxBread',
            'inBoxOther',
            'inCondiments'
        ]
        self.data = self.clean_data(self.data)

    def build(self, buildPath):
        if os.path.isdir(buildPath):
            shutil.rmtree(buildPath)
        os.mkdir(buildPath)
        self.generate_final_document(
            os.path.join(buildPath, "BuyPlan.html"), 
            self.generate_buy_list()
        )
        self.generate_final_document(
            os.path.join(buildPath, "IngredientsByLocation.html"),
            self.generate_ingredients_by_location()
        )
        self.generate_final_document(
            os.path.join(buildPath, "MasterBuyList.html"),
            self.generate_list_of_stores_for_ingredients()
        )
        self.generate_ingredients_list(os.path.join(buildPath, "IngredientsList.txt"))

    def clean_data(self, dirtyData):      
        for eachItem in dirtyData:
            for location in self.storageLocations:
                if eachItem.get(location, False):
                    eachItem['storage'] = location
                if not eachItem.get('storage'):
                    eachItem['storage'] = "NONE"

        #print "* TODO Validate that ingredients are stored in the same place and purchased in the same place"
        #print "* TODO Validate that ingredients have compatible units, or that we know how to convert"
        #print "* TODO Strip out empty rows"
        #print "* TODO Make data lower case unless there is anything we want to preserve."
        return dirtyData

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
            
    def generate_buy_list(self):
        template = env.get_template('BuyList.html')
        data = {"stores":self.get_stores()}
        return template.render(data)
        
    def generate_ingredients_by_location(self):
        template = env.get_template('IngredientsByLocation.html')
        data = {"storageLocations": self.sort_ingred_by_storage()}
        #p(data)
        return template.render(data)
        
    def generate_ingredients_list(self, whereToBuild):
        with open(whereToBuild, 'w') as ingFile:
            ingFile.write('\n'.join(self.ingredients()))
            
    def generate_list_of_stores_for_ingredients(self):
        template = env.get_template('IngredientsStores.html')
        ingStores = {}
        def storeForIngredient(ingredient):
            storesForIng = set([e['buyStore'] for e in self.data if e['item'] == ingredient])
            if len(storesForIng) is 1:
                return list(storesForIng)[0]
            else:
                return ""
        for ingredient in self.ingredients():
            ingStores[ingredient] = storeForIngredient(ingredient)
        return template.render({"ingredients": ingStores})
        
    def generate_final_document(self, whereToBuild, whatToBuildWith):
        with open(whereToBuild, "w") as buildFile:
            buildFile.write(whatToBuildWith)
            
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='''
        Generate reports for menu planning. To use the test ingredients list, type:
        python planner.py ingredients.test.csv'''
    )
    parser.add_argument('csvfile', help='The csv file containing menu information.')
    parser.add_argument('--skip_rows', '-s', help="Number of header rows to skip in the csv file")
    args = parser.parse_args()

    fieldNames = [
        'day',
        'meal',
        'mealType',
        'dish',
        'item',
        'cookingNotes',
        'quantity',
        'inCoolerFrozen',
        'inCoolerCool',
        'inBoxVeg',
        'inBoxFruit',
        'inBoxDry',
        'inBoxBread',
        'inBoxOther',
        'inCondiments',
        'isPrecooked',
        'buyState',
        'buyStore',
        'alternateStore',
        'purchased',
        'buyingNotes'
    ]
    planner = FoodPlanner(args.csvfile, fieldNames, skipRows=args.skip_rows)
    planner.build(BUILD_TARGET)
   

    
