if ! command -v kubectl &>/dev/null; then
  echo "'kubectl' could not be found. Installing ..."
  curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
  chmod +x kubectl
  mv ./kubectl /usr/local/bin/kubectl
fi

if ! command -v kind &>/dev/null; then
  echo "'kind' could not be found. Installing ..."
  curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.14.0/kind-linux-amd64
  chmod +x ./kind
  mv ./kind /usr/local/bin/kind
fi

if ! command -v linkerd &>/dev/null; then
  echo "'linkerd' could not be found. Installing ..."
  curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
  linkerd version
fi

cat >kind-config.yml <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
  extraPortMappings:
  - containerPort: 31080
    hostPort: 80
  - containerPort: 31443
    hostPort: 443
EOF

kind create cluster --name jina-serverless --config kind-config.yml
rm kind-config.yml

echo -e "Installing 'knative' components.."
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.5.0/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.5.0/serving-core.yaml

echo -e "Setting up 'Kourier' Ingress for knative"
kubectl apply -f kourier.yaml
kubectl patch configmap/config-network \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'
kubectl patch configmap/config-domain \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"127.0.0.1.sslip.io":""}}'

# Install linkerd on the cluster
linkerd check --pre
linkerd install | kubectl apply -f -

# Annotate Knative / Kourier with linkerd proxy
declare -a namespaces=("kourier-system" "knative-serving")
kubectl annotate ns kourier-system knative-serving default linkerd.io/inject=enabled

for namespace in "${namespaces[@]}"; do
  kubectl rollout restart deploy -n ${namespace}
  for deployment in $(kubectl get deployments -n ${namespace} -o custom-columns=":metadata.name"); do
    kubectl rollout status deployment ${deployment} -n ${namespace}
  done
done
