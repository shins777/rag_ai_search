docker build --no-cache -t kakao-pay-terms:1.0 ./src/
docker tag kakao-pay-terms:1.0 asia-northeast3-docker.pkg.dev/ai-hangsik/kakao-pay/kakao-pay-terms:1.0
docker push asia-northeast3-docker.pkg.dev/ai-hangsik/kakao-pay/kakao-pay-terms:1.0
gcloud run deploy kakao-pay-terms-run \
	--region=asia-northeast3 \
	--platform managed \
	--allow-unauthenticated \
	--min-instances=3 \
	--max-instances=5 \
	--service-account=gen-ai-access@ai-hangsik.iam.gserviceaccount.com \
	--container=kakao-pay-container1 \
	--image=asia-northeast3-docker.pkg.dev/ai-hangsik/kakao-pay/kakao-pay-terms:1.0  \
	--port=80 --cpu=8 --memory=32Gi