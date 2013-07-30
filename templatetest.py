from jinja2 import Environment, FileSystemLoader
env = Environment(loader=FileSystemLoader('Templates'))

template = env.get_template('BuyList.html')

data = {
	"stores": [
		{
			"name": "Costco", 
			"location" : "CA"
		},
		{
			"name": "Trader Joes",
			"location": "AZ"
		} 
	],
	
	"Message": "These are store names.",
}

print template.render(data)



