import aws_cdk as core
import aws_cdk.assertions as assertions

from aws_multi_s2_s.aws_multi_s2_s_stack import AwsMultiS2SStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_multi_s2_s/aws_multi_s2_s_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsMultiS2SStack(app, "aws-multi-s2-s")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
