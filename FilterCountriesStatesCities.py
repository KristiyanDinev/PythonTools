import json
import requests as rq

res = rq.get('https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/refs/heads/master/json/countries%2Bstates%2Bcities.json')
if not res.ok:
    print('Country data is not available right now')
    exit()

data = json.loads(res.text)

'''
with open('countries+states+cities.json', mode="r", encoding="utf-8") as openfile:
    data = json.load(openfile)
'''


new_data = []

for country in data:

    countryData = {
        "name": country["name"],
        "states": []
    }

    for state in country["states"]:
        stateData = {
            "name": state["name"],
            "cities": []
        }

        for city in state["cities"]:
            stateData["cities"].append({
                "name": city["name"],
            })

        countryData["states"].append(stateData)

    new_data.append(countryData)

# Serializing json
json_object = json.dumps(new_data, indent=4, ensure_ascii=False)

# Writing to sample.json
with open("countries_states_cities.json", mode="w", encoding="utf-8") as outfile:
    outfile.write(json_object)