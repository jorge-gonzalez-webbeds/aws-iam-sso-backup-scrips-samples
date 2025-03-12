import boto3
import json

DEFAULT_REGION = "eu-west-1"

session = boto3.Session(
    aws_access_key_id="",
    aws_secret_access_key="",
)

ssoadminclient = session.client(service_name="sso-admin", region_name=DEFAULT_REGION)

Instances = (ssoadminclient.list_instances()).get("Instances")
newIdCInstanceARN = Instances[0].get("InstanceArn")


def getDescription(permissionSet):
    return (
        permissionSet["Description"]
        if "Description" in permissionSet and permissionSet["Description"] != ""
        else "-"
    )


# To translate set datatype to json
class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


# MAIN
print("\n -------------------------------------- \n")
with open("output/OldPermissionSets.json") as json_file:
    permissionSets = json.load(json_file)
    newPermissionSets = {}

    for permissionSetName, eachPermissionSet in permissionSets.items():
        print(f" -> Creating permission set: {permissionSetName}")

        try:
            newPermissionSet = ssoadminclient.create_permission_set(
                InstanceArn=newIdCInstanceARN,
                Name=permissionSetName,
                Description=getDescription(permissionSet=eachPermissionSet),
            )
        except Exception as e:
            print(f"(E!) -> Error creating permission set {permissionSetName}: {e}")
            print("\n Skipping to the next permission set... \n")
            continue

        managedPolicies, customerManagedPolicies = [], []

        try:
            # Add Managed Policies
            for eachManagedPolicy in eachPermissionSet["ManagedPolicies"]:
                managedPolicy = ssoadminclient.attach_managed_policy_to_permission_set(
                    InstanceArn=newIdCInstanceARN,
                    PermissionSetArn=newPermissionSet["PermissionSet"][
                        "PermissionSetArn"
                    ],
                    ManagedPolicyArn=eachManagedPolicy["Arn"],
                )
                managedPolicies.append(eachManagedPolicy)
                print(f"\t-> Managed Policy {eachManagedPolicy['Name']} added")

            # Add Customer Managed Policies
            for eachCustomerManagedPolicy in eachPermissionSet[
                "CustomerManagedPolicies"
            ]:
                customerManagedPolicy = ssoadminclient.attach_customer_managed_policy_reference_to_permission_set(
                    InstanceArn=newIdCInstanceARN,
                    PermissionSetArn=newPermissionSet["PermissionSet"][
                        "PermissionSetArn"
                    ],
                    CustomerManagedPolicyReference={
                        "Name": eachCustomerManagedPolicy["Name"],
                        "Path": eachCustomerManagedPolicy["Path"],
                    },
                )
                customerManagedPolicies.append(eachCustomerManagedPolicy)
                print(
                    f"\t-> Customer Managed Policy {eachCustomerManagedPolicy['Name']} added"
                )

            permissionSet = {
                "Description": getDescription(
                    permissionSet=newPermissionSet["PermissionSet"]
                ),
                "PermissionSetArn": newPermissionSet["PermissionSet"][
                    "PermissionSetArn"
                ],
                "ManagedPolicies": managedPolicies,
                "CustomerManagedPolicies": customerManagedPolicies,
            }
            newPermissionSets.update(
                {newPermissionSet["PermissionSet"]["Name"]: permissionSet}
            )

            print("\n -------------------------------------- \n")

        except Exception as e:
            print(f"(E!) -> There is an error with the policy: {e}")

with open("output/NewPermissionSets.json", "w") as outfile:
    json.dump(newPermissionSets, outfile, cls=SetEncoder)
