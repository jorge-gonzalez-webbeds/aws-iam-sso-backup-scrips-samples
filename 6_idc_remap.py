import boto3, csv, json
import backoff

session = boto3.Session(profile_name='webbeds-idp2')

ssoadminclient = session.client('sso-admin')

instances= (ssoadminclient.list_instances()).get('Instances')
instanceARN=instances[0].get('InstanceArn')

# wait for account assignment creation status, usually takes <5 seconds
@backoff.on_predicate( # retries until the function returns True
    backoff.constant,  # constant backoff
    interval=4,  # wait _ seconds between each try
    max_time=30)  # maximum wait time is _ seconds
def wait_for_account_assignment_creation_status(instance_arn, assignment_request_id):
    if ssoadminclient.describe_account_assignment_creation_status(
        InstanceArn=instance_arn, 
        AccountAssignmentCreationRequestId=assignment_request_id)['AccountAssignmentCreationStatus']['Status'] == 'SUCCEEDED':
        return True
    return False

def read_large_json(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.loads(file.read())
    except FileNotFoundError:
        print("The file was not found.")
    except json.JSONDecodeError:
        print("The file does not contain valid JSON.")
    except Exception as e:
        print(f"An error occurred: {e}")

entities = read_large_json('output/IdentityReport.json')
newPermissionSets = read_large_json('output/NewPermissionSets.json')

with open('output/OldIdentityStoreReport.csv', 'r') as oldIdCReport:
    reader = csv.DictReader(oldIdCReport)
    oldAssignments = list(reader)
    # CSV Columns: Account ID,Account Name,Permission Set,Principal Type,Principal
    for assignment in oldAssignments:
        try:
            response = ssoadminclient.create_account_assignment(
                InstanceArn=instanceARN,
                PermissionSetArn=newPermissionSets[assignment['Permission Set']]['PermissionSetArn'],
                PrincipalType=assignment['Principal Type'],
                PrincipalId=entities[assignment['Principal']]['id'], # --> ID from new IdC Report
                TargetId=assignment['Account ID'],
                TargetType='AWS_ACCOUNT'
            )

            # wait for the association to be created
            if not wait_for_account_assignment_creation_status(
                instanceARN,
                response['AccountAssignmentCreationStatus']['RequestId']
            ):
                failure_reason = ssoadminclient.describe_account_assignment_creation_status(
                    InstanceArn=instanceARN, AccountAssignmentCreationRequestId=response['AccountAssignmentCreationStatus']['RequestId'])['AccountAssignmentCreationStatus']['FailureReason']
                raise ValueError(f"Timeout - reason {failure_reason}")

            print(f"Successfully created assignment for {assignment['Permission Set']} and {assignment['Principal']}\n")
        except Exception as e:
            print(f"There is an error in {assignment['Permission Set']}: {e}")
            exit()
    
    # Remap applications and assignments from OldApplications to new IdC
    applications = read_large_json('output/OldApplications.json')
    for application in applications:
        try:
            # Create the application
            NewAppArn = ssoadminclient.create_application(
                ApplicationProviderArn=application['ApplicationDetails']['ApplicationProviderArn'],
                Description=application['ApplicationDetails']['Description'] if 'Description' in application['ApplicationDetails'] else '-',
                InstanceArn=instanceARN,
                Name=application['ApplicationDetails']['Name'],
                PortalOptions=application['ApplicationDetails']['PortalOptions'],
                Status=application['ApplicationDetails']['Status'],
                Tags=application['ApplicationDetails']['Tags'] if 'Tags' in application['ApplicationDetails'] else [],
            )
            # Set assignment configuration and authentication method
            ssoadminclient.put_application_assignment_configuration(
                ApplicationArn=NewAppArn,
                AssignmentRequired=application['AssignmentConfiguration']['AssignmentRequired'],
            )
            if application['AuthenticationMethod']:
                ssoadminclient.put_application_authentication_method(
                    ApplicationArn=NewAppArn,
                    AuthenticationMethodType=application['AuthenticationMethod']['AuthenticationMethodType'],
                    AuthenticationMethodConfiguration=application['AuthenticationMethod']['AuthenticationMethodConfiguration'],
                )

            # Create assignments
            for assignment in application['Assignments']:
                ssoadminclient.create_application_assignment(
                    ApplicationArn=NewAppArn,
                    PermissionSetArn=newPermissionSets[application['ApplicationDetails']['Name']]['PermissionSetArn'],
                    PrincipalType=assignment['PrincipalType'],
                    PrincipalId=entities[assignment['PrincipalName']]['id'],
                    TargetId=assignment['TargetId'] if 'TargetId' in assignment else '',
                    TargetType=assignment['TargetType'] if 'TargetId' in assignment else ''
                )
            print(f"Successfully created application assignment for {application['ApplicationName']} and {application['PrincipalId']}\n")
        except Exception as e:
            print(f"There is an error in {application['ApplicationName']}: {e}")
            exit()