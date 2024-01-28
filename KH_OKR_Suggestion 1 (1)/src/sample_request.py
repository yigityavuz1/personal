import requests

params_obj = {
    "ObjectiveID": "0001",
    "Objective": "Şirket içi satışları arttırmak"
}

params_kr = {
    "SessionID": "96B889AE-CFDC-497B-920A-970FF861C6D4",
    "UserID": "48D689C9-7A92-436D-3D48-08D9DAD35B22",
    "KeyResultID": "0001",
    "KeyResult": "Şirket içi satışları arttırmak"
}

params_chat = {
    "SessionID": "96B889AE-CFDC-497B-920A-970FF861C6D4",
    "UserID": "48D689C9-7A92-436D-3D48-08D9DAD35B22",
    "UserName": "Zeynep Akant",
    "CompanyName": "KoçDigital",
    "CompanyGroup": "Koç Group",
    "Department": "AI Business Solutions",
    "Position": "Data Scientist",
    "HireDate": "May 2022",
    "UserMessage": "",
    "ChatHistory": []
}

# response = requests.post('http://localhost:3000/improve_objective/', json=params_obj)
# response = requests.post('http://localhost:3000/improve_key_result/', json=params_kr)
response = requests.post('http://localhost:3000/aligned_okr_suggestion_chat/', json=params_chat)


print(response.json())
