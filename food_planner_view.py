from jinja2 import Environment, FileSystemLoader
import shutil
import os
import inspect
# A little trick. Now I can call p(valueIwantToPrint) and see it nicely
from pprint import pprint as p
env = Environment(loader=FileSystemLoader('Templates'))

class FoodPlannerView(object):

    def __init__(self, csvFileName, fieldNames, skipRows=0):
        pass

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
   
