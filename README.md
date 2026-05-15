# csvapp — DevOps Case Study

A production-grade CSV processing web application with full Kubernetes deployment, CI/CD pipeline, and cloud storage integration.

---

## Architecture

```
                        GitHub Actions CI/CD
                               │
                    ┌──────────▼──────────┐
                    │   Build & Push       │
                    │   Docker Image       │
                    │   (DockerHub)        │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Helm Deploy        │
                    │   to Kubernetes      │
                    └──────────┬──────────┘
                               │
              ┌────────────────▼────────────────┐
              │         Kubernetes Cluster        │
              │                                   │
              │  ┌─────────────────────────────┐  │
              │  │           Pod               │  │
              │  │  ┌──────────┐ ┌──────────┐  │  │
              │  │  │  Nginx   │ │  Flask   │  │  │
              │  │  │ sidecar  │ │   app    │  │  │
              │  │  └────┬─────┘ └────┬─────┘  │  │
              │  │       └─────┬──────┘         │  │
              │  │         emptyDir             │  │
              │  │       (shared static)        │  │
              │  └─────────────────────────────┘  │
              │              │ HPA                 │
              │    ┌─────────▼──────────┐         │
              │    │   NodePort Service  │         │
              └────┴────────────────────┴─────────┘
                               │
                    ┌──────────▼──────────┐
                    │       AWS S3         │
                    │   Processed Files    │
                    │                     │
                    │  Standard (0-30d)   │
                    │       ↓             │
                    │  Glacier IR (30-90d)│
                    │       ↓             │
                    │  Deep Archive (90d+)│
                    └─────────────────────┘
```

---

## Project Structure

```
csvapp/
├── app/
│   ├── app.py                 # Flask application
│   ├── requirements.txt       # Python dependencies
│   ├── Dockerfile             # Container definition
│   └── templates/
│       ├── index.html         # Upload + file list UI
│       └── result.html        # CSV display table
├── helm/
│   └── csvapp/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml  # Nginx sidecar + Flask pod
│           ├── service.yaml     # NodePort service
│           └── hpa.yaml         # Horizontal Pod Autoscaler
├── terraform/
│   └── main.tf               # S3 bucket + Glacier lifecycle
├── ansible/
│   ├── playbook.yml
│   ├── vars/main.yml
│   └── roles/csvapp/tasks/main.yml
├── kops/
│   └── cluster.yaml          # Multi-IG cluster with spot + on-demand
└── .github/workflows/
    └── ci-cd.yaml            # Build → Push → Deploy pipeline
```

---

## Application

### What It Does
- Upload any CSV file (soh.csv format: Product ID, Name, Price)
- Parse and display all rows in the browser as a table
- Upload processed file to S3 (or local storage in dev mode)
- Show history of previously processed files

### Running Locally

```bash
cd app
pip install -r requirements.txt
python app.py
# Visit http://localhost:5000
```

### Running with Docker

```bash
cd app
docker build -t csvapp .
docker run -p 5000:5000 csvapp
```

---

## Kubernetes Deployment

### Prerequisites
- Minikube or EKS cluster running
- kubectl configured
- Helm 3 installed

### Deploy with Helm

```bash
# Start Minikube
minikube start

# Deploy
helm install csvapp ./helm/csvapp

# Get URL
minikube service csvapp-service --url

# Check pods (should see 2 containers per pod: app + nginx)
kubectl get pods
kubectl describe pod <pod-name>
```

### Verify Nginx Sidecar

```bash
# Both containers running in same pod
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[*].name}'
# Output: app nginx

# Shared emptyDir volume
kubectl describe pod <pod-name> | grep -A5 "Volumes"
```

### Autoscaling

```bash
# HPA is automatically created
kubectl get hpa

# Watch scaling in action
kubectl run -it --rm load-generator --image=busybox \
  -- /bin/sh -c "while true; do wget -q -O- http://csvapp-service/; done"
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```
Push to main
    │
    ├── Test (pip install + import check)
    │
    ├── Build & Push Docker image to DockerHub
    │       adarshsinghdxb/csvapp:latest
    │       adarshsinghdxb/csvapp:<git-sha>
    │
    └── Helm upgrade --install to Kubernetes
```

### Required GitHub Secrets

| Secret | Value |
|--------|-------|
| `DOCKERHUB_USERNAME` | `adarshsinghdxb` |
| `DOCKERHUB_TOKEN` | DockerHub access token |
| `KUBECONFIG` | base64-encoded kubeconfig |

---

## Infrastructure (Terraform)

### S3 + Glacier Lifecycle

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

**Lifecycle policy:**
- Day 0–30: S3 Standard
- Day 30–90: Glacier Instant Retrieval
- Day 90+: Glacier Deep Archive
- Day 365: Deleted

---

## Kubernetes Cluster Config (kops)

`kops/cluster.yaml` defines a production-grade cluster with:

| Instance Group | Type | Lifecycle | Min | Max |
|---|---|---|---|---|
| master-us-east-1a | t3.medium | On-demand | 1 | 1 |
| master-us-east-1b | t3.medium | On-demand | 1 | 1 |
| nodes-ondemand | t3.medium/large | On-demand | 2 | 5 |
| nodes-spot | t3.medium/large | Spot | 0 | 10 |

Cluster Autoscaler is enabled for all node groups.

---

## Configuration Management (Ansible)

```bash
cd ansible

# Deploy with Ansible
ansible-playbook -i inventory/hosts.yml playbook.yml

# Only update configs
ansible-playbook -i inventory/hosts.yml playbook.yml --tags config

# Only redeploy Helm
ansible-playbook -i inventory/hosts.yml playbook.yml --tags helm
```

---

## Design Decisions

**Nginx sidecar over NFS:** Used `emptyDir` shared volume between Flask app and Nginx sidecar within the same pod. This avoids NFS complexity and network latency — static files are copied at pod start via an init container and served directly by Nginx.

**Spot + On-demand mix:** On-demand nodes provide baseline stability for critical pods; spot nodes handle burst traffic at 60-70% cost reduction.

**Glacier tiering:** SOH CSV files are operationally relevant for ~30 days, then archivable. Deep Archive at 90 days provides near-zero storage cost for compliance retention.
