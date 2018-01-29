from bs4 import BeautifulSoup, element
import requests
import json
import pickle

def extract_company_data(soup):
    company_data = []

    max_rows = 1e5
    row_num = 0

    category = ""
    category_titles = []
    company_datatypes = []
    data_and_purposes = []

    company_categories = []

    for row in soup.find("table").find_all("tr"):
        row_num += 1

        # Skip the initial header row
        if row_num == 1:
            continue

        # Fields with colspan=4 mark new categories
        td = row.find("td")    
        if td and "colspan" in td.attrs.keys():

            if "Please note" in td.text:
                continue # This is the note under 'Credit Reference and Fraud Agencies', not a new section

            category_parts = td.text.split(".")
            category_num = category_parts[0].strip()
            category_name = (".").join(category_parts[1:]).strip()

            category_titles.append({"name": category_name, "id": category_num, "frequency": 0})
            continue

        # Pick out the children of this <tr> tag that are tags
        row_data = []
        for c in row.contents:
            if isinstance(c, element.Tag):
                row_data.append(c.text)            


        data_and_purpose = {"data": row_data[3].strip(), "purpose": row_data[2].strip()}
        if data_and_purpose not in data_and_purposes:
            data_and_purposes.append(data_and_purpose)
        data_and_purpose_index = data_and_purposes.index(data_and_purpose)

        for company in split_company_string(row_data[1].strip()):  

            category_titles[-1]["frequency"] += 1

            company_data.append({"company_name": company, "data_and_purpose_index": data_and_purpose_index, "category_num": category_num, "category_name": category_name})

            for dataType in splitDataTypes(row_data[3].strip()):
                company_datatypes.append({"company_name": company, "dataType": dataType, "category_name": category_name, "data_and_purpose_index": data_and_purpose_index})

            #all_company_list.append({"company": company, "data_and_purpose_index": data_and_purpose_index})

            company_category = {"company": company, "category": category_name}
            if company_category in company_categories:
                category_titles[-1]["frequency"] -= 1 # company has already been counted

            company_categories.append(company_category)

        # limit number of rows processed, for easier debugging    
        if row_num == max_rows:
            break
            
    return company_data, category_titles, company_datatypes, data_and_purposes



def split_company_string(company_string):

    company_string = company_string.replace(", Inc", " Inc")
    company_string = company_string.replace(", LLC.", " LLC")
    company_string = company_string.replace(", LLC", " LLC")
    company_string = company_string.replace(", and ", ", ")
    company_string = company_string.replace(" and ", ", ")


    companies = []
    in_parens = False
    name = ""

    # split on commas or semicolons not in brackers
    for c in company_string:

        if c == "(":
            in_parens = True

        if c == ")":
            in_parens = False

        if (c == "," or c == ";") and not in_parens:
            companies.append(name.strip())
            name = ""
            continue

        name = name + c

    companies.append(name)
    return companies

def splitDataTypes(str1):
    
    str1 = str1.lower()
    str1 = str1.replace(", and", ", ")
    str1 = str1.replace("and", ",")
    str1 = str1.replace("e-mail", "email")
    
    purposes = str1.split(",")
    purposes = map(lambda x: x.strip(), purposes)
    purposes = filter(lambda x: len(x) > 0, purposes)
    purposes = map(lambda x: x[0:-1] if x[-1]=="." else x, purposes)
    
    
    return list(set(purposes)) # we shouldn't report the same keyword more than once


# TODO: count keywords in main function
def count_keywords(company_data, data_and_purposes):
    counts = {}
    
    for c in company_data:
        #if accept[c["data"]] != "y":
        #    continue
        
        data = data_and_purposes[c["data_and_purpose_index"]]["data"]
        for keyword in splitDataTypes(data):
            if keyword not in counts.keys():
                counts[keyword] = 0
            counts[keyword] += 1

    results = []
    for key in counts:
        results.append({"dataType": key, "frequency": counts[key]})

    return results


def aggregate_category_counts(company_data, company_datatypes):
    
    counts = {}
    
    for use in company_datatypes:
        category_name = use["category_name"]
        dataType = use["dataType"]

        if category_name not in counts.keys():
            counts[category_name] = {}

        if dataType not in counts[category_name].keys():
            counts[category_name][dataType] = 0
          
        counts[category_name][dataType] += 1
              
    result = []
    for category_name in counts.keys():
       for dataType in counts[category_name].keys():
          result.append({"category_name": category_name, "dataType": dataType, "frequency": counts[category_name][dataType]})
                      
    return result
    

def write_output(company_data):
    output = open('paypal.json', 'w')
    json.dump(company_data, output)




result = requests.get("https://www.paypal.com/ie/webapps/mpp/ua/third-parties-list")
c = result.content
soup = BeautifulSoup(c, 'html.parser')
print "PARSED"

#inputFile = open('valid.pkl', 'rb')
#pickle.load(inputFile)

company_data, category_titles, company_datatypes, data_and_purposes = extract_company_data(soup)
print "got companies"

data_types = count_keywords(company_data, data_and_purposes)
print "got data types"

category_datatypes = aggregate_category_counts(company_data, company_datatypes)
print "got category_datatypes"

write_output({"category_titles": category_titles,  "dataTypes": data_types, "companyDataTypes": company_datatypes, "category_datatypes": category_datatypes, "data_and_purposes": data_and_purposes})
