import boto3, json, csv

session = boto3.Session(profile_name="webbeds-idp")

idstoreclient = session.client("identitystore")
ssoadminclient = session.client("sso-admin")
orgsclient = session.client("organizations")

users = {}
groups = {}
permissionSets = {}
permissionSetsData = {}
Accounts = {}
applications = []

Instances = (ssoadminclient.list_instances()).get("Instances")
InstanceARN = Instances[0].get("InstanceArn")
IdentityStoreId = Instances[0].get("IdentityStoreId")


def mapUserIDs():
    """
    Create a dictionary mapping User IDs to usernames.

    This function retrieves all users from the AWS Identity Store and creates
    a dictionary where the key is the User ID and the value is the username.
    The result is stored in the global 'users' dictionary.

    Note:
        This function uses pagination to handle large numbers of users.
    """
    ListUsers = idstoreclient.list_users(IdentityStoreId=IdentityStoreId)
    ListOfUsers = ListUsers["Users"]
    while "NextToken" in ListUsers.keys():
        ListUsers = idstoreclient.list_users(
            IdentityStoreId=IdentityStoreId, NextToken=ListUsers["NextToken"]
        )
        ListOfUsers.extend(ListUsers["Users"])
    for eachUser in ListOfUsers:
        users.update({eachUser.get("UserId"): eachUser.get("UserName")})


def mapGroupIDs():
    """
    Create a dictionary mapping Group IDs to display names.

    This function retrieves all groups from the AWS Identity Store and creates
    a dictionary where the key is the Group ID and the value is the display name.
    The result is stored in the global 'groups' dictionary.

    Note:
        This function uses pagination to handle large numbers of groups.
    """
    ListGroups = idstoreclient.list_groups(IdentityStoreId=IdentityStoreId)
    ListOfGroups = ListGroups["Groups"]
    while "NextToken" in ListGroups.keys():
        ListGroups = idstoreclient.list_groups(
            IdentityStoreId=IdentityStoreId, NextToken=ListGroups["NextToken"]
        )
        ListOfGroups.extend(ListGroups["Groups"])
    for eachGroup in ListOfGroups:
        groups.update({eachGroup.get("GroupId"): eachGroup.get("DisplayName")})


def GetDescription(permissionSet):
    """
    Retrieve the description of a permission set.

    Args:
        permissionSet (dict): A dictionary containing permission set details.

    Returns:
        str: The description of the permission set if available, otherwise an empty string.
    """
    return permissionSet.get("Description") if "Description" in permissionSet else ""


def mapPermissionSetIDs():
    """
    Create dictionaries mapping permission set ARNs to names and detailed information.

    This function retrieves all permission sets from AWS SSO, and for each:
    1. Creates a mapping of permission set ARNs to names in the global 'permissionSets' dictionary.
    2. Creates a detailed information dictionary in the global 'permissionSetsData' dictionary.

    The detailed information includes:
    - ID
    - Description
    - Permission Set ARN
    - Managed Policies
    - Customer Managed Policies

    Note:
        This function uses pagination to handle large numbers of permission sets.
        TODO: Implement pagination for managed policies and customer managed policies.
    """
    ListPermissionSets = ssoadminclient.list_permission_sets(InstanceArn=InstanceARN)
    ListOfPermissionSets = ListPermissionSets["PermissionSets"]
    while "NextToken" in ListPermissionSets.keys():
        ListPermissionSets = ssoadminclient.list_permission_sets(
            InstanceArn=InstanceARN, NextToken=ListPermissionSets["NextToken"]
        )
        ListOfPermissionSets.extend(ListPermissionSets["PermissionSets"])
    for eachPermissionSet in ListOfPermissionSets:
        permissionSetDescription = ssoadminclient.describe_permission_set(
            InstanceArn=InstanceARN, PermissionSetArn=eachPermissionSet
        )
        permissionSetDetails = permissionSetDescription.get("PermissionSet")

        # Get Managed policies --> TODO: Deal with pagination
        managedPolicies = ssoadminclient.list_managed_policies_in_permission_set(
            InstanceArn=InstanceARN, PermissionSetArn=eachPermissionSet
        )

        # Get Customer Managed Policies --> TODO: Deal with pagination
        customerManagedPolicies = (
            ssoadminclient.list_customer_managed_policy_references_in_permission_set(
                InstanceArn=InstanceARN, PermissionSetArn=eachPermissionSet
            )
        )

        permissionSet = {
            "Id": eachPermissionSet.split("/")[-1],
            "Description": GetDescription(permissionSet=permissionSetDetails),
            "PermissionSetArn": permissionSetDetails.get("PermissionSetArn"),
            "ManagedPolicies": managedPolicies.get("AttachedManagedPolicies"),
            "CustomerManagedPolicies": customerManagedPolicies.get(
                "CustomerManagedPolicyReferences"
            ),
        }
        permissionSetsData.update({permissionSetDetails["Name"]: permissionSet})

        permissionSets.update(
            {
                permissionSetDetails.get("PermissionSetArn"): permissionSetDetails.get(
                    "Name"
                )
            }
        )


def ListAccountsInOrganization():
    """
    Retrieve and store information about all accounts in the AWS Organization.

    This function fetches details of all accounts in the organization and stores
    them in the global 'Accounts' dictionary, where the key is the Account ID
    and the value is the Account Name.

    Note:
        This function uses pagination to handle large numbers of accounts.
    """
    AccountsList = orgsclient.list_accounts()
    ListOfAccounts = AccountsList["Accounts"]
    while "NextToken" in AccountsList.keys():
        AccountsList = orgsclient.list_accounts(NextToken=AccountsList["NextToken"])
        ListOfAccounts.extend(AccountsList["Accounts"])
    for eachAccount in ListOfAccounts:
        # Accounts.append(str(eachAccount.get('Id')))
        Accounts.update({eachAccount.get("Id"): eachAccount.get("Name")})


def GetPermissionSetsProvisionedToAccount(AccountID):
    """
    Retrieve the list of permission sets provisioned to a specific AWS account.

    Args:
        AccountID (str): The ID of the AWS account to check.

    Returns:
        list: A list of permission set ARNs provisioned to the account.

    Note:
        This function uses pagination to handle large numbers of permission sets.
    """
    ListOfPermissionSetsProvisionedToAccount = []
    PermissionSetsProvisionedToAccount = (
        ssoadminclient.list_permission_sets_provisioned_to_account(
            InstanceArn=InstanceARN, AccountId=AccountID
        )
    )
    try:
        ListOfPermissionSetsProvisionedToAccount = PermissionSetsProvisionedToAccount[
            "PermissionSets"
        ]
        while "NextToken" in PermissionSetsProvisionedToAccount.keys():
            PermissionSetsProvisionedToAccount = (
                ssoadminclient.list_permission_sets_provisioned_to_account(
                    InstanceArn=InstanceARN,
                    AccountId=AccountID,
                    NextToken=PermissionSetsProvisionedToAccount["NextToken"],
                )
            )
            ListOfPermissionSetsProvisionedToAccount.extend(
                PermissionSetsProvisionedToAccount["PermissionSets"]
            )
        return ListOfPermissionSetsProvisionedToAccount
    except:
        return ListOfPermissionSetsProvisionedToAccount


def ListAccountAssignments(AccountID):
    """
    Retrieve all permission set assignments for a specific AWS account.

    This function fetches all permission sets provisioned to the account and then
    retrieves the assignments (user or group) for each permission set.

    Args:
        AccountID (str): The ID of the AWS account to check.

    Returns:
        list: A list of dictionaries, each containing details of an assignment.

    Note:
        This function uses pagination to handle large numbers of assignments.
    """
    PermissionSetsList = GetPermissionSetsProvisionedToAccount(AccountID)
    Assignments = []
    for permissionSet in PermissionSetsList:
        AccountAssignments = ssoadminclient.list_account_assignments(
            InstanceArn=InstanceARN, AccountId=AccountID, PermissionSetArn=permissionSet
        )
        Assignments.extend(AccountAssignments["AccountAssignments"])
        while "NextToken" in AccountAssignments.keys():
            AccountAssignments = ssoadminclient.list_aaccount_assignments(
                InstanceArn=InstanceARN,
                AccountId=AccountID,
                PermissionSetArn=permissionSet,
                NextToken=AccountAssignments["NextToken"],
            )
            Assignments.extend(AccountAssignments["AccountAssignments"])
    return Assignments


def ListApplications():
    """
    Create a report of all the applications configured in IdC.
    """
    ListOfApplications = []
    Applications = ssoadminclient.list_applications(InstanceArn=InstanceARN)
    ListOfApplications.extend(Applications["Applications"])
    while "NextToken" in Applications.keys():
        Applications = ssoadminclient.list_applications(
            InstanceArn=InstanceARN, NextToken=Applications["NextToken"]
        )
        ListOfApplications.extend(Applications["Applications"])
    # For each app add scope, assignment and auth information
    for app in ListOfApplications:
        AppARN = app["ApplicationArn"]
        # Get application details
        AppDetails = ssoadminclient.describe_application(ApplicationArn=AppARN)
        # Substitute datetime by string
        AppDetails["CreatedDate"] = AppDetails["CreatedDate"].strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Get assignment configuration
        AppAssignment = ssoadminclient.get_application_assignment_configuration(
            ApplicationArn=AppARN
        )

        # Get authentication method configuration
        try:
            AppAuthMethod = ssoadminclient.get_application_authentication_method(
                ApplicationArn=AppARN
            )
        except:
            AppAuthMethod = {}

        # Get application assignments
        AppAssignments = []
        assignments = ssoadminclient.list_application_assignments(ApplicationArn=AppARN)
        AppAssignments.extend(assignments["ApplicationAssignments"])

        # Handle pagination for assignments
        while "NextToken" in assignments:
            assignments = ssoadminclient.list_application_assignments(
                ApplicationArn=AppARN, NextToken=assignments["NextToken"]
            )
            AppAssignments.extend(assignments["ApplicationAssignments"])

        # Build application configuration object
        AppConfig = {
            "ApplicationDetails": AppDetails,
            "AssignmentConfiguration": AppAssignment,
            "AuthenticationMethod": AppAuthMethod,
            "Assignments": [
                {
                    "PrincipalId": assignment.get("PrincipalId"),
                    "PrincipalType": assignment.get("PrincipalType"),
                    "PrincipalName": (
                        users.get(assignment.get("PrincipalId"))
                        if assignment.get("PrincipalType") == "USER"
                        else groups.get(assignment.get("PrincipalId"))
                    ),
                }
                for assignment in AppAssignments
            ],
        }
        applications.append(AppConfig)


class SetEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle set objects.

    This encoder extends the default JSON encoder to properly serialize set objects
    by converting them to lists.
    """

    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def GenerateFiles():
    """
    Generate CSV and JSON reports based on AWS IAM Identity Center (formerly AWS SSO) assignments.

    This function performs the following tasks:
    1. Retrieves account assignments for each account in the organization.
    2. Generates a CSV report ('OldIdentityStoreReport.csv') containing account assignments.
    3. Creates a JSON file ('OldPermissionSets.json') with detailed permission set information.
    4. Creates a JSON file ('OldApps.json) with detailed application information.

    The CSV report includes the following columns:
    - Account ID
    - Account Name
    - Permission Set
    - Principal Type
    - Principal (User or Group name)

    The PermissionSet file contains detailed information about each permission set, including:
    - ID
    - Description
    - Permission Set ARN
    - Managed Policies
    - Customer Managed Policies

    The application file contains detailed information about each application, including:
    - Application details
    - Assignment configuration
    - Authentication method
    - Assignments (users and groups)
    ...

    Raises:
        Exception: If there's an error processing a specific account ID.

    Note:
        This function relies on several global variables and helper functions
        that should be initialized and defined before calling this function.
    """
    ListOfAccountIDs = list(Accounts.keys())
    entries = []
    for eachAccountID in ListOfAccountIDs:
        try:
            GetAccountAssignments = ListAccountAssignments(eachAccountID)
            for eachAssignment in GetAccountAssignments:
                entry = []
                entry.append(eachAssignment.get("AccountId"))
                entry.append(Accounts.get(eachAssignment.get("AccountId")))
                entry.append(permissionSets.get(eachAssignment.get("PermissionSetArn")))
                entry.append(eachAssignment.get("PrincipalType"))
                if eachAssignment.get("PrincipalType") == "GROUP":
                    entry.append(groups.get(eachAssignment.get("PrincipalId")))
                else:
                    entry.append(users.get(eachAssignment.get("PrincipalId")))
                entries.append(entry)
        except Exception as e:
            print("Error in Account ID: " + eachAccountID + " " + str(e))
            continue

    headers = [
        "Account ID",
        "Account Name",
        "Permission Set",
        "Principal Type",
        "Principal",
    ]

    with open("output/OldIdentityStoreReport.csv", "x") as report:
        csvwriter = csv.writer(report)
        csvwriter.writerow(headers)
        csvwriter.writerows(entries)
    print("Done! 'OldIdentityStoreReport.csv' report is generated successfully!")

    with open("output/OldPermissionSets.json", "x") as fp:
        json.dump(permissionSetsData, fp, cls=SetEncoder)
    print("Done! 'OldPermissionSets.json' has been generated successfully!")

    with open("output/OldApplications.json", "x") as fp:
        json.dump(applications, fp, cls=SetEncoder, indent=2)
    print("Done! 'OldApplications.json' has been generated successfully!")


# MAIN
mapUserIDs()
mapGroupIDs()
ListAccountsInOrganization()
mapPermissionSetIDs()
ListApplications()
GenerateFiles()
