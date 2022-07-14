# dhos-encounters-api Integration Tests
This folder contains service-level integration tests for the dhos-encounters-api.

## Running the tests
```
# run tests
$ make test-local

# inspect test logs
$ docker logs dhos-encounters-integration-tests

# cleanup
$ docker-compose down
```

## Test development
For test development purposes you can keep the service running and keep re-running only the tests:
```
# in one terminal screen bring up the docker environment (note this will also run the tests)
$ docker-compose up --force-recreate

# in the other terminal screen you can now run the tests
$ DHOS_SERVICES_BASE_URL=http://localhost:5555 \
  DHOS_ENCOUNTERS_BASE_URL=http://localhost:5000 \
  SYSTEM_JWT_SCOPE="read:send_encounter write:send_encounter read:gdm_encounter write:gdm_encounter write:gdm_patient write:gdm_patient_all write:send_patient write:send_location write:gdm_location" \
  HS_ISSUER=http://localhost/ \
  HS_KEY=secret \
  PROXY_URL=http://localhost \
  RABBITMQ_HOST=localhost \
  RABBITMQ_USERNAME=guest \
  RABBITMQ_PASSWORD=guest \
  RABBITMQ_NOENCRYPT="true" \
  behave --no-capture --logging-level DEBUG

# Don't forget to clean up when done!
$ docker-compose down
```
