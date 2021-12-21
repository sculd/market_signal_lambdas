rm my-deployment-package.zip
rm -rf ./package
mkdir package
pip install --target ./package -r requirements.txt
cd package                                        
zip -r ../my-deployment-package.zip .
cd ..
zip -g my-deployment-package.zip lambda_function.py
zip -g my-deployment-package.zip k8s/secrets/config.json
aws s3 cp my-deployment-package.zip s3://market-stream-publisher-okcoin-lambda/
aws lambda update-function-code --function-name MarketStreamPublisherOkcoin --s3-bucket market-stream-publisher-okcoin-lambda --s3-key my-deployment-package.zip
