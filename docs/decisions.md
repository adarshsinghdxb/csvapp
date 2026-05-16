# Solution Overview

This is my submission for the DevOps case study. I'll walk through what I built and why.

## What I built

A simple CSV processing web app deployed on Kubernetes, with CI/CD, S3 storage and all the infra config they asked for.

## The App

Built with Python Flask. You upload a CSV, it parses it and shows the data in a table in the browser. Once processed it uploads the file to S3. You can also see previously uploaded files on the homepage.

Used Flask because it's lightweight and straightforward for this kind of thing. No need to overcomplicate it with Django for a simple file processing app.

## Kubernetes Setup

Deployed using Helm on Minikube locally. The Helm chart creates a deployment with two containers in the same pod - Nginx as a sidecar and the Flask app. They share files through an emptyDir volume (not NFS as required). Nginx serves static files, Flask handles the actual app logic.

Service is exposed via NodePort. HPA is configured to scale between 2 and 5 replicas based on CPU.

## kops Cluster Config

Created a kops cluster config with multiple instance groups - one on-demand group for stable baseline workloads and one spot group that can scale to zero when not needed. Cluster autoscaler is enabled for both. This gives you cost savings on spot while keeping stability on on-demand.

## Ansible

Ansible role manages the Kubernetes configs - secrets, configmaps and Helm deployment. This way app configs live in Ansible and not hardcoded anywhere.

## S3 and Glacier

Terraform provisions the S3 bucket with versioning, encryption and a lifecycle policy. Files move to Glacier Instant Retrieval after 30 days and Deep Archive after 120 days. After a year they get deleted. Stock on hand files are only really useful for a month so this makes sense from a cost perspective.

## CI/CD

GitHub Actions pipeline triggers on push to main. It runs tests, builds the Docker image, pushes to DockerHub and deploys to Kubernetes using Helm.

## What I would do differently with more time

- Hook up proper secrets management instead of env vars
- Add a proper ingress instead of NodePort
- Set up monitoring with Prometheus and Grafana
- Write proper tests for the Flask app
