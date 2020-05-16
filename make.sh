
function create-secrets(){
    kubectl create secret generic db-user-pass  --from-file=./private/password.txt
    kubectl create secret generic odatests-tests-bot-password  --from-file=./private/testbot-password.txt
    kubectl create secret generic odatests-secret-key  --from-file=./private/secret-key.txt
    kubectl create secret generic minio-key  --from-file=./private/minio-key.txt
    kubectl create secret generic jena-password  --from-file=./private/jena-password.txt
    kubectl create secret generic logstash-entrypoint  --from-file=./private/logstash-entrypoint.txt
}

function template() {
    (cd odatests; make image-name)

    < odatests-deployment-template.yaml sed 's@{{IMAGE}}@'$(cat image-name)'@' > odatests-deployment.yaml
}

function deploy() {
    template

    kubectl apply -f odatests-deployment.yaml
    rm -f odatests-deployment.yaml
}

$@
