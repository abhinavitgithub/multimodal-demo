# VPS & Deployment Infrastructure Provider Comparison (TIAV Deployment)

> **Scope:** Evaluation of VPS, Cloud Compute, and PaaS hosting options for deploying the TIAV FastAPI backend and frontend.
> **Last updated:** May 2026

---

## 🏗️ TIAV Deployment Architecture

The TIAV application offloads LLM processing to OpenRouter, separating the application compute layer from the heavy model inference layer:

```text
       Frontend (Web / Android)
                  ↓
         TIAV FastAPI Backend
                  ↓
             OpenRouter
                  ↓
  Switchable Models (Qwen / Claude / GPT / NIM etc.)
```

**Key Architectural Insight:** Since LLM inference is managed externally by **OpenRouter**, the TIAV FastAPI backend is primarily responsible for light routing, orchestrating requests, database queries, and serving the frontend. **Dedicated local GPU compute is NOT required** for standard production, making high-performance CPU hosting the most practical and cost-effective approach.

---

## 📊 Deployment Provider Overview

| Provider | Hosting Type | CPU/GPU | Ease of Setup | Approx Cost | Scaling | Best Use Case | Notes |
|---|---|---|---|---|---|---|---|
| **Hetzner** | Unmanaged VPS / Dedicated | CPU-Optimized (GPU on dedicated only) | Medium (Manual Linux / Docker setup) | **Very Low** (~$4 - $30/mo) | Manual (Vertical resize or manual load balancer) | **Cheapest & High-Performance** production hosting | Unmatched price-to-performance ratio; best raw compute value. |
| **DigitalOcean** | Managed VPS (Droplets) / PaaS | CPU-Only | Easy (Intuitive UI, 1-click Docker Droplets) | **Low-Medium** (~$6 - $40/mo) | Moderate (Simple horizontal/vertical scaling) | **Production-Ready** startups and independent devs | Excellent developer portal, managed databases, and highly reliable SLA. |
| **AWS EC2** | IaaS VPS | Flexible CPU & GPU instances | Hard (Complex networking, IAM, VPC setup) | **Medium-High** ($15+/mo base + egress/EBS) | Excellent (Auto Scaling Groups, ELB integration) | **Enterprise** deployments with deep AWS integrations | Extremely reliable, industry-standard, but complex billing and setup. |
| **Azure VM** | IaaS VPS | Flexible CPU & GPU instances | Hard (Enterprise console, complex IAM/vNets) | **Medium-High** (Competitive with AWS) | Excellent (Virtual Machine Scale Sets) | **Enterprise** corporate environments with MS contracts | Seamless Active Directory/SSO integration. Complex pricing structure. |
| **GCP Compute Engine** | IaaS VPS | Flexible CPU & GPU instances | Medium-Hard (VPC, IAM, gcloud CLI) | **Medium-High** (Sustained use discounts) | Excellent (Managed Instance Groups) | **Enterprise** leveraging GCP's big data/analytics | High-performance internal networking; easy migration to Cloud Run. |
| **RunPod** | Serverless GPU / GPU VPS (Pods) | Dedicated GPU + CPU | Easy-Medium (Docker-based templates) | **High** (~$100+/mo for persistent VMs) | Easy (Serverless GPU endpoints / multi-pod) | Custom model fine-tuning or secondary local LLMs | **GPU-Heavy** but redundant for TIAV due to OpenRouter integration. |
| **Vast.ai** | Peer-to-peer rented GPU hosting | High-end Consumer & Enterprise GPUs | Medium (Docker, SSH/Jupyter) | **Low for GPU** (~$0.10 - $1.50/hr) | Poor (No native auto-scaler, nodes can go offline) | Non-critical batch jobs or temporary model tests | No SLA/uptime guarantees. Highly discouraged for persistent FastAPI. |
| **Paperspace** | Cloud GPU / Core Virtual Machines | Dedicated CPU VMs & Powerful GPUs | Easy-Medium (Web console, Docker templates) | **Medium** (From ~$0.07/hr CPU to $1.50+/hr GPU) | Easy (Simple API scaling, dedicated VMs) | **GPU-Heavy** with permanent storage & SLA | Reliable alternative to RunPod/Vast.ai with persistent storage. |
| **Railway** | Developer Platform (PaaS) | CPU-Only | **Very Easy** (Git push deploy, auto FastAPI) | **Low-Medium** (~$5 base + usage) | Automatic (Simple horizontal scaling) | **Easiest** rapid MVP prototyping and deployment | Incredible developer experience. Auto SSL, zero-config CI/CD, and DBs. |
| **Render** | Developer Platform (PaaS) | CPU-Only | **Very Easy** (Git-integrated deployment) | **Low-Medium** (~$7/mo for Web Services) | Easy (Autoscaling slider / configuration) | **Easiest** persistent production web app hosting | Very user-friendly. Built-in DDoS protection, auto SSL, zero-config. |

---

## 🏆 Quick Recommendations for TIAV Deployment

* **🟢 Cheapest (Best Value CPU):** **Hetzner**
  * *Why:* Offers unmatched CPU and RAM specifications for the price, making it ideal for persistent, low-budget, high-throughput production hosting.
* **🔵 Easiest (Best Developer Experience):** **Railway** or **Render**
  * *Why:* Zero-config deployment directly from your Git repository. Handles automatic SSL certificates, database hosting, and CI/CD out-of-the-box.
* **🏢 Enterprise-Grade (Complex & Highly Scalable):** **AWS EC2**, **GCP Compute Engine**, or **Azure VM**
  * *Why:* Perfect if your organization requires rigid enterprise security policies, complex VPC setups, or needs to hook directly into active cloud infrastructures.
* **🟠 GPU-Heavy (Alternative/Secondary Local Inference):** **Paperspace** or **RunPod**
  * *Why:* If you decide to host a secondary lightweight local model (like Nemotron-Mini) alongside OpenRouter, Paperspace provides dedicated SLA-backed persistent GPU VMs.
* **🛡️ Production-Ready (Balanced Compute & DevOps ease):** **DigitalOcean**
  * *Why:* The ideal middle ground between unmanaged VPS and complex cloud platforms. Offers reliable SLAs, managed databases, and basic Kubernetes setups.