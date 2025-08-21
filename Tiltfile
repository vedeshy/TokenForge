# Tiltfile for TokenForge

# Load Docker Compose
docker_compose('docker-compose.yaml')

# Build API server
local_resource(
    'api-build',
    'cd api && go build -o ../bin/api',
    deps=['api/']
)

# Run API server
local_resource(
    'api-run',
    'bin/api',
    deps=['bin/api'],
    resource_deps=['api-build', 'postgres', 'minio'],
    serve_cmd=True
)

# Watch config files
watch_file('configs/models.yaml')
watch_file('configs/runtimes.yaml')
watch_file('configs/benchmark.yaml')

# Port forwards
k8s_resource('api', port_forwards='8080:8080')
k8s_resource('grafana', port_forwards='3000:3000')
k8s_resource('prometheus', port_forwards='9090:9090')
k8s_resource('minio', port_forwards=['9000:9000', '9001:9001'])
k8s_resource('postgres', port_forwards='5432:5432')
