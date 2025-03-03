import boto3, json

session = boto3.Session(profile_name='webbeds-idp2')

idstoreclient = session.client('identitystore')
ssoadminclient = session.client('sso-admin')
orgsclient= session.client('organizations')

report = {}

Instances= (ssoadminclient.list_instances()).get('Instances')
InstanceARN=Instances[0].get('InstanceArn')
IdentityStoreId=Instances[0].get('IdentityStoreId')

# Dictionary mapping User IDs to usernames
def mapUserIDs():
    ListUsers=idstoreclient.list_users(IdentityStoreId=IdentityStoreId)
    ListOfUsers=ListUsers['Users']
    while 'NextToken' in ListUsers.keys():
        ListUsers=idstoreclient.list_users(IdentityStoreId=IdentityStoreId,NextToken=ListUsers['NextToken'])
        ListOfUsers.extend(ListUsers['Users'])
    for eachUser in ListOfUsers:
        report.update({eachUser.get('UserName'): {
                'id': eachUser.get('UserId'),
                'type': 'USER'
            }
        })


# Dictionary mapping Group IDs to display names
def mapGroupIDs():
    ListGroups=idstoreclient.list_groups(IdentityStoreId=IdentityStoreId)
    ListOfGroups=ListGroups['Groups']
    while 'NextToken' in ListGroups.keys():
        ListGroups=idstoreclient.list_groups(IdentityStoreId=IdentityStoreId,NextToken=ListGroups['NextToken'])
        ListOfGroups.extend(ListGroups['Groups'])
    for eachGroup in ListOfGroups:
        report.update({eachGroup.get('DisplayName'): {
                'id': eachGroup.get('GroupId'),
                'type': 'GROUP'
            }
        })

# To translate set datatype to json
class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

# MAIN
mapUserIDs()
mapGroupIDs()

with open("output/IdentityReport.json", "w") as outfile:
    json.dump(report, outfile, cls=SetEncoder)
print("Done! IdentityReport.json generated successfully!")
