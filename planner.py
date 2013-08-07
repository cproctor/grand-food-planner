#! /usr/bin/python
# Check out the line above. This is a trick--when you try to execute a file, 
# the terminal peeks into the first line. If it finds a #! and then a path, 
# it uses the program at that path to execute the file. 
# 1. Make this file executable by typing chmod u+x planner.py
#    (chmod changes permissions. You're giving the (u)ser e(x)ecute permissions
#    on planner.py)
# 2. Now you can just type ./planner.py and it'll go!

# Import all the classes we need from other modules
# From each module, we import a class. A module is a bunch of code--one file--
# which can contain anything. We're following good code style by defining
# one class in each module.
from food_planner_model import FoodPlannerModel
from food_planner_view import FoodPlannerView
from spreadsheet_loader import SpreadsheetLoader

# We also import argparse, which allows us to define and read arguments 
# passed in to the program.
import argparse

# Now we define some constants. We could have passed these in to the program
# as arguments, but who has time for that? Each of these tells our program
# how to handle a particular spreadsheet--the URL it should be loaded from,
# the filename where it can be found locally, the number of junk rows at the 
# top that should be skipped, and a list of the field names.
INGREDIENTS = {
    "url": 'https://docs.google.com/spreadsheet/ccc?key=0Au3OsR7L9ksedGpJdHRGWjlOaVFtZzkxRUhESEl6YlE&output=csv&gid=26',
    "file": 'ingredients.csv',
    "rowsToSkip": 0,
    "fieldNames" : [
        'name',
        'buyStore',
        'buyStoreAlternate',
        'notes'
    ]
 }
MENUS = {
    "url": 'https://docs.google.com/spreadsheet/ccc?key=0Au3OsR7L9ksedGpJdHRGWjlOaVFtZzkxRUhESEl6YlE&output=csv&gid=19',
    "file": 'menus.csv',
    "rowsToSkip": 4,
    "fieldNames": [
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
 }
PURCHASES = {
    "url":'https://docs.google.com/spreadsheet/ccc?key=0Au3OsR7L9ksedGpJdHRGWjlOaVFtZzkxRUhESEl6YlE&output=csv&gid=27',
    "file": 'purchases.csv',
    "rowsToSkip": 1,
    "fieldNames": [
        'name',
        'count',
        'unitsPerCount',
        'unit',
        'description',
        'shoppingTrip',
        'notes',
        'day',
        'meal'
    ]
 }
BUILD_TARGET = '_build'

# Let's actually start the program. Note that we no longer use the 
# if __name__ == '__main__' check because there's nothing in this module
# anyone else would ever want to import. Any time this code is run, it's 
# because we intend for the following things to happen.

# set up the argument parser by defining arguments that might be passed in.
parser = argparse.ArgumentParser(description='''
    Generate reports for menu planning. To use the test ingredients list, type:
    python planner.py ingredients.test.csv'''
)
parser.add_argument('--reload', '-r', default=False, action="store_true",
        help="Reload the data files before running")
parser.add_argument('--warnings', '-w', default=False, action="store_true",
        help="Show warnings")
parser.add_argument('--verbose', '-v', default=False, action="store_true",
        help="Display lots of information about what's going on")

# We're done defining the arguments, so we can now tell the parser to look at 
# what got passed in and to make sense of it as the arguments we defined.
args = parser.parse_args()

# If the reload flag (--reload or -r shorthand) was set, we should load the 
# csv files from Google Docs before we go on...
if args.reload:
    # So we'll make a spreadsheet loader
    loader = SpreadsheetLoader(verbose=True)
    # And have it go get our files
    loader.load([INGREDIENTS, MENUS, PURCHASES])

# Now we create the model, telling it where to find its files and how
# to make sense of them.
model = FoodPlannerModel(ingredients=INGREDIENTS, menus=MENUS, 
        purchases=PURCHASES, warnings=args.warnings, verbose=args.verbose)
# Now we create the view, giving it the model as its data source
view = FoodPlannerView(model)
# Finally, tell the view to render, creating all the html files we want.
view.build(BUILD_TARGET)
