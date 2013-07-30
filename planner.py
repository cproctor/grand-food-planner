import csv

class FoodPlanner(object):

    def __init__(self, csvFileName, fieldNames, skipRows=0):
        with open(csvFileName) as csvFile:
            reader = csv.DictReader(csvFile, fieldNames)
            for badRow in range(skipRows):
                reader.read()
            self.data = [row for row in reader]
        self.data = self.clean_data(self.data)
        print self.data

    def clean_data(self, dirtyData):
        storageLocations = [
            'inCoolerFrozen',
            'inCoolerCool',
            'inBoxVeg',
            'inBoxFruit',
            'inBoxDry',
            'inBoxBread',
            'inBoxOther',
            'inCondiments'
        ]
        for datum in dirtyData:
            for location in storageLocations:
                if datum.get(location, False):
                    datum['storage'] = location
        return dirtyData
        

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='''
        Generate reports for menu planning. To use the test ingredients list, type:
        python planner.py ingredients.test.csv'''
    )
    parser.add_argument('csvfile', help='The csv file containing menu information.')
    args = parser.parse_args()

    fieldNames = [
        'day',
        'meal',
        'mealType',
        'dish',
        'item',
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
        'purchased',
        'notes'
    ]
    planner = FoodPlanner(args.csvfile, fieldNames)

    
