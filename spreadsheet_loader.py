import requests

# With this class, we can reload spreadsheets from Google Docs automatically
# whenever we want them!
class SpreadsheetLoader(object):
    "A tool to load csv spreadsheets from Google Docs and save them to files"

    # This function runs when a new instance of SpreadsheetLoader is created.
    # You can pass verbose=True if you want to hear all about it. 
    def __init__(self, verbose=False):
        "Initialize an instance of SpreadsheetLoader"
        # Store this value in this instance so we can look it up later
        self.verbose = verbose

    def load(self, spreadsheets):
        "Try to load each spreadsheet"
        for eachSpreadsheet in spreadsheets:
            self.load_spreadsheet(eachSpreadsheet)
    
    # Here's the meat--try to load the URL. If successful, write its contents
    # to a file. Note that the first statement in this method is a string. That's 
    # called a docstring; you can call help(SpreadsheetLoader.load_spreadsheet)
    # and it'll return the docstring. Thus, we provide help for both the reader
    # of this code and the user of the code in one place. Typically, a docstring
    # briefly explains what a method does and comments before the method
    # (this text) explain how it works.
    def load_spreadsheet(self, spreadsheet):
        "Load the provided url and write its contents to a file"

        # Start by letting the user know what's going on
        self.log("Attempting to load a spreadsheet...")
        self.log("Reading from URL %s" % spreadsheet['url'])

        # The requests.get method loads a URL
        response = requests.get(spreadsheet['url'])

        # Check to see whether the response came back successfully.
        # HTTP responses come with status codes (404 means not found; 500 means 
        # server error; 200 means OK) If we don't get a 200, something went wrong
        # (wrong URL?) and we should abort.
        if response.status_code != 200:
            self.log("Error reading URL; status code %s" % response.status_code)
            raise IOError("Could not read URL %s" % spreadsheet['url'])

        # If we got here, then the response came back successfully.
        self.log("Successfully fetched a CSV file of %s lines." % 
                len(response.content.split('\n')))
        # Now, open the file
        self.log("Writing the CSV data to %s" % spreadsheet['file'])
        with open(spreadsheet['file'], 'w') as destinationFile:
            destinationFile.write(response.content)

    # If we want to change the way logging works, redefine this method.
    # Right now, logging just prints to the screen, but a more robust
    # method would be to have the instance accept a log stream, and to 
    # log into it.
    def log(self, message, level="INFO"):
        "Log a message"
        # If not verbose, say nothing.
        if self.verbose:
            print message
        
