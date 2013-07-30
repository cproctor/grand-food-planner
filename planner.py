
class FoodPlanner(object):
    def __init__(self, csvfile):
        print csvfile

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate reports for menu planning.')
    parser.add_argument('csvfile', help='The csv file containing menu information.')
    args = parser.parse_args()

    planner = FoodPlanner(args.csvfile)

    
