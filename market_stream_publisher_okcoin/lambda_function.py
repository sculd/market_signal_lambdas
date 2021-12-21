import json
import boto3

def get_task_arns(ecs_client, group_name):
  tasks = ecs_client.list_tasks(cluster='market-signal')
  return [task_arn for task_arn in tasks['taskArns'] if ecs_client.describe_tasks(tasks = [task_arn], cluster='market-signal')['tasks'][0]['group'] == group_name]

def start_task(group_name, container_name, task_definition, command):
  envvars = json.load(open('k8s/secrets/config.json'))

  client = boto3.client('ecs')

  task_arsns = get_task_arns(client, group_name)

  for task_arn in task_arsns:
    print('deleting an ecs task {}'.format(task_arn))
    response = client.stop_task(
      cluster='market-signal',
      task=task_arn
    )

  response = client.run_task(
    cluster = 'market-signal',
    launchType = 'FARGATE',
    taskDefinition = task_definition,
    count = 1,
    group = group_name,
    platformVersion = 'LATEST',
    networkConfiguration = {
      'awsvpcConfiguration': {
          'subnets': [
              'subnet-0694757b',
              'subnet-70e04b1b'
          ],
          'assignPublicIp': 'ENABLED'
      }
    },
    overrides = {
      'containerOverrides': [
          {
              'name': container_name,
              'command': command,
              'environment': [{'name': k, 'value': v} for k, v in envvars.items()]
          },
      ]
    }
  )
  return str(response)

def lambda_handler(event, context):
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps(start_task('market_stream_publisher_okcoin', 'market_stream_publisher_okcoin', 'market_stream_publisher_okcoin:1', ['python', 'run.py', 'okcoin']))
    }
