import io

from aiohttp import web, ClientSession
import boto3
from settings import (
    AMAZON_S3_CONFIG as s3_config,
    BUCKET_NAME,
    RECONGIZE_URL,
    PLACE_TO_STORE,
)
from botocore.exceptions import ClientError
import logging
import uuid
import os
import PIL.Image as Image


async def upload_to_aws(client, filename):
    """загружаем на бакет"""
    object_name = str(uuid.uuid4())
    filename_on_disk = prepare_file(filename, object_name)
    try:
        client.upload_file(filename_on_disk, BUCKET_NAME, f'{object_name}.jpeg')
    except (ClientError, ValueError) as e:
        logging.error(e)
        os.system(f"rm {PLACE_TO_STORE}/{filename_on_disk}")
        return {"error": e}
    return {"res": {"object_name": f"{object_name}.jpeg", "filename": filename_on_disk}}


async def remove_everywhere(client, filename_on_aws, filename_on_disk):
    """удаляем с бакета"""
    await client.delete_object(Bucket=BUCKET_NAME, Key=filename_on_aws)
    os.remove(filename_on_disk)


def prepare_file(file, future_name):
    """конввертим и сохраняет как джипег"""
    file_place = f"{PLACE_TO_STORE}/{future_name}.jpeg"
    if not os.path.exists(PLACE_TO_STORE):
        os.makedirs(PLACE_TO_STORE)
    lines = []
    with open(file_place, "+wb") as f:
        for line in file.readlines():
            lines.append(line)
    webp_image = Image.open(io.BytesIO(b''.join(lines)))
    jpg_buffer = io.BytesIO()
    webp_image.convert("RGB").save(jpg_buffer, format="JPEG")
    jpg_image_bytes = jpg_buffer.getvalue()
    with open(file_place, "+wb") as f:
        f.write(jpg_image_bytes)
    return file_place


async def check_geste(request):
    """проверка жеста на лямбде"""
    s3_client = boto3.client("s3", **s3_config)
    post = await request.post()
    avatar_path = post.get("avatar")
    selfie_path = post.get("selfie")
    geste = post.get("geste")
    aws_avatar = await upload_to_aws(s3_client, avatar_path.file)
    aws_selfie = await upload_to_aws(s3_client, selfie_path.file)
    res = False
    if not "err" in aws_avatar and not "err" in aws_selfie:
        async with ClientSession() as session:
            selfie = aws_selfie.get("res").get("object_name")
            avatar = aws_avatar.get("res").get("object_name")
            response = await session.post(
                url=RECONGIZE_URL,
                json={
                    "s3_selfie_key": selfie,
                    "s3_avatar_key": avatar,
                    "sign_to_check": geste,
                },
                headers={
                    "Content-Type": "application/json",
                },
            )
            res = await response.json()
    await remove_everywhere(
        client=s3_client,
        filename_on_aws=avatar,
        filename_on_disk=aws_avatar.get("res").get("filename"),
    )
    await remove_everywhere(
        client=s3_client,
        filename_on_aws=selfie,
        filename_on_disk=aws_selfie.get("res").get("filename"),
    )
    return web.json_response({"result": res.get('result')})


async def health_check(request):

    return web.json_response({"result": True})


app = web.Application()
app.router.add_route("GET", "/health-check", health_check)
app.router.add_route("POST", "/proof_geste", check_geste)

if __name__ == "__main__":
    web.run_app(app, port=8888)
