rm my-deployment-package.zip
rm -rf ./package
mkdir package
pip install --target ./package -r requirements.txt
cd package                                        
zip -r ../my-deployment-package.zip .
cd ..
zip -g my-deployment-package.zip lambda_function.py
zip -g my-deployment-package.zip report.py
zip -g my-deployment-package.zip report_email.py
zip -g my-deployment-package.zip report_sms.py
aws s3 cp my-deployment-package.zip s3://market-moves-lambda/
aws lambda update-function-code --function-name MarketSignal --s3-bucket market-moves-lambda --s3-key my-deployment-package.zip
