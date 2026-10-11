import os

import boto3
from moto import mock_aws


def main():
    # Dummy values for this local simulation, not real AWS credentials.
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_EC2_METADATA_DISABLED"] = "true"

    # Start the simulation BEFORE creating the AWS client.
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")

        bucket_name = "cloudguard-demo-bucket"

        s3.create_bucket(Bucket=bucket_name)
        print(f"Created simulated bucket: {bucket_name}")

        s3.put_object(
            Bucket=bucket_name,
            Key="hello.txt",
            Body=b"Hello from CloudGuard!",
        )
        print("Stored object: hello.txt")

        response = s3.get_object(
            Bucket=bucket_name,
            Key="hello.txt",
        )

        contents = response["Body"].read().decode("utf-8")
        print(f"Read object: {contents}")

        assert contents == "Hello from CloudGuard!"
        print("PASS: The stored text matches the original text.")

    print("Simulation finished. Temporary resources cleared.")


if __name__ == "__main__":
    main()