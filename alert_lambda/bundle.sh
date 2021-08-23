rm my-deployment-package.zip
rm -rf ./package
mkdir package
pip install --target ./package -r requirements.txt
cd package                                        
zip -r ../my-deployment-package.zip .
cd ..
zip -g my-deployment-package.zip lambda_function.py
zip -g my-deployment-package.zip authorize.py
zip -g my-deployment-package.zip get.py
zip -g my-deployment-package.zip remove.py
zip -g my-deployment-package.zip post.py
aws s3 cp my-deployment-package.zip s3://market-signal-lambda/
