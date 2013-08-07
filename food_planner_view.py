from jinja2 import Environment, FileSystemLoader
import shutil
import os
import inspect
# A little trick. Now I can call p(valueIwantToPrint) and see it nicely
from pprint import pprint as p
env = Environment(loader=FileSystemLoader('Templates'))

class FoodPlannerView(object):

    def __init__(self, model):
        self.model = model

    def build(self, buildPath):
        if os.path.isdir(buildPath):
            shutil.rmtree(buildPath)
        os.mkdir(buildPath)
        self.generate_final_document(
            os.path.join(buildPath, "BuyList.html"), 
            self.generate_buy_list()
        )
        self.generate_final_document(
            os.path.join(buildPath, "PackList.html"), 
            self.generate_pack_list()
        )
        self.generate_final_document(
            os.path.join(buildPath, "CookList.html"), 
            self.generate_cook_list()
        )
        self.generate_final_document(
            os.path.join(buildPath, "index.html"), 
            self.generate_index()
        )

    def generate_buy_list(self):
        template = env.get_template('BuyList.html')
        data = self.model.get_buy_list()
        return template.render(data)

    def generate_pack_list(self):
        template = env.get_template('PackList.html')
        data = self.model.get_pack_list()
        return template.render(data)

    def generate_cook_list(self):
        template = env.get_template('CookList.html')
        data = self.model.get_cook_list()
        return template.render(data)

    def generate_index(self):
        template = env.get_template('index.html')
        data = self.model.get_time()
        return template.render(data)

        
    def generate_final_document(self, whereToBuild, whatToBuildWith):
        with open(whereToBuild, "w") as buildFile:
            buildFile.write(whatToBuildWith)
   
