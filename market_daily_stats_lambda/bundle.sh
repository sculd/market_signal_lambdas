rm my-deployment-package.zip
rm -rf ./package
mkdir package
pip install --target ./package -r requirements.txt
cd package                                        
zip -r ../my-deployment-package.zip .
cd ..
zip -g my-deployment-package.zip lambda_function.py
aws s3 cp my-deployment-package.zip s3://market-daily-stat-lambda/
aws lambda update-function-code --function-name MarketDailyStat --s3-bucket market-daily-stat-lambda --s3-key my-deployment-package.zip
