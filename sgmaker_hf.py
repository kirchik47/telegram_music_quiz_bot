import sagemaker
import boto3
from sagemaker.huggingface import get_huggingface_llm_image_uri, HuggingFaceModel
import json


sess = sagemaker.Session()
sagemaker_session_bucket = 'llama_music'
if sagemaker_session_bucket is None and sess is not None:
    sagemaker_session_bucket = sess.default_bucket()

try:
    role = sagemaker.get_execution_role()
except ValueError:
    iam = boto3.client('iam')
    role = iam.get_role(RoleName='sagemaker-full-access')['Role']['Arn']

sess = sagemaker.Session(default_bucket=sagemaker_session_bucket)
llm_image = get_huggingface_llm_image_uri('huggingface', version='1.0.3')

instance_type = "ml.g5.xlarge"
number_of_gpu = 1
health_check_timeout = 300

config = {
  'HF_MODEL_ID': "meta-llama/Meta-Llama-3.1-8B-Instruct", 
  'SM_NUM_GPUS': json.dumps(number_of_gpu), 
  'MAX_INPUT_LENGTH': json.dumps(1024), 
  'MAX_TOTAL_TOKENS': json.dumps(2048),
}
llm_model = HuggingFaceModel(
  role=role,
  image_uri=llm_image,
  env=config
)
# llm = llm_model.deploy(
#   initial_instance_count=1,
#   instance_type=instance_type,
#   container_startup_health_check_timeout=health_check_timeout,
# )
