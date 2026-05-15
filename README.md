# csvapp

Simple web app to upload and process CSV files. Built with Python Flask.

## How to run locally

```bash
cd app
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000 and upload soh.csv

## Run with Docker

```bash
cd app
docker build -t csvapp .
docker run -p 5000:5000 csvapp
```

## Deploy on Kubernetes

```bash
minikube start
helm install csvapp ./helm/csvapp
minikube service csvapp-service --url
```

## S3 setup

```bash
cd terraform
terraform init
terraform apply
```

Creates S3 bucket with Glacier lifecycle. Files move to Glacier after 30 days.

## CI/CD

Push to main triggers GitHub Actions which builds Docker image, pushes to DockerHub and deploys to Kubernetes.

## Folder structure

```
app/          Flask app
helm/         Kubernetes deployment
terraform/    S3 bucket
ansible/      Config management
kops/         Cluster config
docs/         Architecture diagram
.github/      CI/CD pipeline
```
