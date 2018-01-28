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

    for row in soup.find("table").find_all("tr"):
        row_num += 1

        # Skip the initial header row
        if row_num == 1:
            continue

        # Fields with colspan=4 mark new categories
        td = row.find("td")    
        if td and "colspan" in td.attrs.keys():

            category_parts = td.text.split(".")
            category_num = category_parts[0].strip()
            category_name = (".").join(category_parts[1:]).strip()

            category_titles.append({"name": category_name, "id": category_num})

            continue

        # Pick out the children of this <tr> tag that are tags
        row_data = []
        for c in row.contents:
            if isinstance(c, element.Tag):
                row_data.append(c.text)            

        for company in split_company_string(row_data[1]):   
            company_data.append({"company_name": company, "purpose": row_data[2], "data": row_data[3], "category_num": category_num, "category_name": category_name})

            for dataType in splitDataTypes(row_data[3]):
                company_datatypes.append({"company_name": company, "dataType": dataType, "category_name": category_name })

        # limit number of rows processed, for easier debugging    
        if row_num == max_rows:
            break
            
    return company_data, category_titles, company_datatypes



def split_company_string(company_string):

    company_string = company_string.replace(", Inc", " Inc")
    company_string = company_string.replace(", and ", ", ")
    company_string = company_string.replace(" and ", ", ")


    companies = []
    in_parens = False
    name = ""

    # split on commas not in brackers
    for c in company_string:

        if c == "(":
            in_parens = True

        if c == ")":
            in_parens = False

        if c == "," and not in_parens:
            companies.append(name.strip())
            name = ""
            continue

        name = name + c
        
    return companies

def splitDataTypes(str1):
    
    str1 = str1.lower()
    str1 = str1.replace(", and", ", ")
    str1 = str1.replace("and", ",")
    
    purposes = str1.split(",")
    purposes = map(lambda x: x.strip(), purposes)
    purposes = filter(lambda x: len(x) > 0, purposes)
    purposes = map(lambda x: x[0:-1] if x[-1]=="." else x, purposes)
    
    
    return list(set(purposes)) # we shouldn't report the same keyword more than once



def count_keywords(company_data):
    counts = {}
    
    for c in company_data:
        #if accept[c["data"]] != "y":
        #    continue
        
        for keyword in splitDataTypes(c["data"]):
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

company_data, category_titles, company_datatypes = extract_company_data(soup)
print "got companies"

data_types = count_keywords(company_data)
print "got data types"

category_datatypes = aggregate_category_counts(company_data, company_datatypes)
print "got category_datatypes"

write_output({"category_titles": category_titles, "companies": company_data, "dataTypes": data_types, "companyDataTypes": company_datatypes, "category_datatypes": category_datatypes})