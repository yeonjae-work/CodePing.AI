"""AWS S3 client for diff storage."""

from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    logger.warning("boto3 not installed, S3 upload disabled")
    BOTO3_AVAILABLE = False


class S3Client:
    """AWS S3 client for uploading large diff files."""
    
    def __init__(self):
        if not BOTO3_AVAILABLE:
            raise RuntimeError("boto3 not available")
        
        self.bucket = os.environ.get("AWS_S3_BUCKET")
        if not self.bucket:
            raise ValueError("AWS_S3_BUCKET environment variable required")
        
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name=os.environ.get("AWS_REGION", "us-east-1"),
        )
    
    async def upload_diff(self, key: str, content: bytes) -> str:
        """Upload diff content to S3 and return the S3 URL."""
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType="text/plain",
                ContentEncoding="gzip",
                ACL="private",
            )
            
            s3_url = f"s3://{self.bucket}/{key}"
            logger.info("Uploaded diff to S3: %s (%d bytes)", s3_url, len(content))
            return s3_url
            
        except ClientError as exc:
            logger.exception("Failed to upload diff to S3: %s", exc)
            raise
    
    def get_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for downloading a diff file."""
        
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as exc:
            logger.exception("Failed to generate presigned URL: %s", exc)
            return None 