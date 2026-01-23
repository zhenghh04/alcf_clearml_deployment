# Setting up ClearML server

1. Requesting VM, have the following three ports open: 8080, 8081, 8001

2. Docker compose files: ClearML will send the three files 'docker-compose.yml', 'docker-compose.override.yml', and 'constants.env' which need to be put inside /opt/allegro/"

    * Change to the constant.env
    ```text
    APISERVER_URL_FOR_EXTERNAL_WORKERS="http://amsc-clearml.alcf.anl.gov:8008"
    WEBSERVER_URL_FOR_EXTERNAL_WORKERS="http://amsc-clearml.alcf.anl.gov:8080"
    FILESERVER_URL_FOR_EXTERNAL_WORKERS="http://amsc-clearml.alcf.anl.gov:8081"
    TASK_ROUTER_URL="http://amsc-clearml.alcf.anl.gov:80/service"
    ```
    * Changes to docker-compose.override.yml
        * Add the following lines
        ```yaml
        webserver:
            environment:
            - WEBSERVER__displayedServerUrls={"apiServer":"$APISERVER_URL_FOR_EXTERNAL_WORKERS","filesServer":"$FILESERVER_URL_FOR_EXTERNAL_WORKERS"}
        ```
        * change http://apiserver:8008 to http://amsc-clearml.alcf.anl.gov:8008 under
        ```yaml 
        environment:
        - CLEARML_API_HOST=http://amsc-clearml.alcf.anl.gov:8008
        ```
3. Run ```setup.sh``` 

3. Recompose 
    ```bash
    sudo docker-compose --env-file constants.env down
    sudo docker-compose --env-file constants.env up -d
    ```
