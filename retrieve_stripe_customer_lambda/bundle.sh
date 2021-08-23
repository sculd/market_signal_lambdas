rm my-deployment-package.zip
rm -rf ./package
mkdir package
pip install --target ./package -r requirements.txt
cd package                                        
zip -r ../my-deployment-package.zip .
cd ..
zip -g my-deployment-package.zip lambda_function.py
zip -g my-deployment-package.zip authorize.py
aws s3 cp my-deployment-package.zip s3://retrieve-stripe-customer-lambda/
aws lambda update-function-code --function-name RetrieveStripeCustomer --s3-bucket retrieve-stripe-customer-lambda --s3-key my-deployment-package.zip
