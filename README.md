# jina-serverless-demo

## What is serverless?

From [wikipedia](https://en.wikipedia.org/wiki/Serverless_computing)

> Serverless computing is a cloud computing execution model in which the cloud provider allocates machine resources on demand, taking care of the servers on behalf of their customers. "Serverless" is a misnomer in the sense that servers are still used by cloud service providers to execute code for developers. However, developers of serverless applications are not concerned with capacity planning, configuration, management, maintenance, fault tolerance, or scaling of containers, VMs, or physical servers.

## Why do we care?

- There are many use cases in jina, which doesn't need Executors or Gateway to be always alive.
- Scale-to-0 saves a lot of cost.
- Enables pay-per-use model of pricing.
- Serverless allows invocations to be "event-driven". Though this demo only shows the event to be triggered by `jina.Client`, we can build different integrations where any [Cloudevent](https://cloudevents.io/) can possibly be converted into a `jina.Client` request.

## Why Knative?

- Knative allows us to scale from 0 to N, based on.
  - `number of simultaneous requests per replica` ([concurrency](https://knative.dev/docs/serving/autoscaling/concurrency/)) or
  - `requests-per-second per replica` ([rps](https://knative.dev/docs/serving/autoscaling/rps-target/))
  - We can set min/max replicas per deployment.
  - It also supports HPA (default CPU based 1-to-N scaling provided by K8S)

### Set-up

> You can skip this step if you already have a k8s cluster & setup knative / linkerd components.

Let's start by setting up a local environment where serverless machinery can be demonstrated. Following script installs

- `kubectl`, `kind` & `linkerd` CLI, if not already installed.
- A local `kind` cluster named `jina-serverless`.
- Knative components
- Kourier Ingress for Knative
- Linkerd components
- Patch Knative & Kourier deployments with Linkerd service-mesh

```bash
bash setup.sh
```

### Define a Flow

We write a dummy `HeavyExecutor` which sleeps for 3 seconds every time it receives a new request. This can be replaced with any heavy Executor.

```yaml
# flow.yml
jtype: Flow
executors:
  - name: heavy_executor
    uses: jinahub+docker://HeavyExecutor
```

### Convert Flow to K8S yaml

Now that we have the setup done, let's use the jina CLI to export a dummy Flow yaml into K8S specific yamls.

```bash
jina export kubernetes flow.yml jina-sls --k8s-namespace jina-sls
```

### Convert to Knative yaml

> This step is temporary and should be implemented as a feature in core.

Knative doesn't understand K8S `Deployment` & `Service` and implements a `Service` under `serving.knative.dev/v1` CRD. Let's convert the K8S yamls to Knative yamls.

```bash
kubectl create namespace jina-sls
kubectl apply -R -f $(python kn/change_to_kn.py jina-sls)
```

We might need to wait a bit until all knative objects are setup in addition to the deployments in `jina-sls` namespace. To check the URL of the gateway, you can use the following command.

```bash
GATEWAY=$(kubectl get ksvc -n jina-sls gateway --no-headers -o custom-columns="URL:.status.url")
echo -e "Flow Gateway is $GATEWAY"
```

Before any Client sends requests to the Gateway, let's check & wait until each deployment has 0 replicas.

<p align="center">
<a href="#"><img src="./.github/before.png" alt="0 replicas" width="100%"></a>
</p>

### Let's send requests to the Flow that doesn't exist!

Let's start 10 concurrent Clients that will send requests to the Gateway. Each request is supposed to take 3 secs when a Flow is deployed with at least 1 replica.

```bash
python load.py 10
```

Note the following.

- As soon as we run the `load.py` script with 10 concurrent clients, new replicas of the `gateway` & `heavy_executor` start spawning.
- After a cool down period, all deployments reach the original state of 0 replicas each.

(Better gif to be uploaded)

<p align="center">
<a href="#"><img src="./.github/serverless.gif" alt="Autoscale from 0 to 10" width="100%"></a>
</p>
