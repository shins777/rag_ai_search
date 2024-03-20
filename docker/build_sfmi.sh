docker build -f ../src/Dockerfile --no-cache -t sfmi-terms:1.0 ../src/ 
docker tag sfmi-terms:1.0 asia-northeast3-docker.pkg.dev/ai-hangsik/sfmi/sfmi-terms:1.0
docker push asia-northeast3-docker.pkg.dev/ai-hangsik/sfmi/sfmi-terms:1.0
gcloud run deploy sfmi-terms-run \
	--region=asia-northeast3 \
	--project=ai-hangsik \
	--platform managed \
	--allow-unauthenticated \
	--min-instances=3 \
	--max-instances=5 \
	--service-account=gen-ai-access@ai-hangsik.iam.gserviceaccount.com \
	--container=sfmi-container1 \
	--image=asia-northeast3-docker.pkg.dev/ai-hangsik/sfmi/sfmi-terms:1.0  \
	--port=80 --cpu=8 --memory=32Gi