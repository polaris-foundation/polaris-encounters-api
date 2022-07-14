Feature: Encounter management
    As a clinician
    I want to search for encounters
    So that I can find the patients' information fast

    Background:
        Given a valid system JWT
        And RabbitMQ is running
        And there exists a location
        And there exists a patient

    Scenario: Patient has no encounters
        When the clinician tries to search for latest encounter by patient uuid
        Then the attempt fails
        When the clinician tries to search for latest encounter by a list of patient UUIDs
        Then the attempt fails

    Scenario: Search for patients with encounters
        Given the patient has a local encounter
        When the clinician retrieves patients with encounters by a list of patient UUIDs
        Then search results contain 1 patient

    Scenario: Latest encounter for patient with closed parent encounter
        Given the clinician creates an epr encounter
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the clinician creates a child encounter of encounter 1
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the clinician closes encounter 1
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And an AUDIT_MESSAGE message is published to RabbitMQ
        When the clinician searches for latest encounter by patient uuid
        Then the search result returns encounter 1

    Scenario: Latest encounter for patient with closed child encounter
        Given the clinician creates an epr encounter
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the clinician creates a child encounter of encounter 1
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the clinician closes encounter 2
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And an AUDIT_MESSAGE message is published to RabbitMQ
        When the clinician searches for latest encounter by patient uuid
        Then the search result returns encounter 1

    Scenario: Latest encounter for patient with deleted parent encounter
        Given the clinician creates an epr encounter
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the clinician creates a child encounter of encounter 1
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the clinician deletes encounter 1
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And an AUDIT_MESSAGE message is published to RabbitMQ
        When the clinician tries to search for latest encounter by patient uuid
        Then the attempt fails

    Scenario: Latest encounter for patient with deleted child encounter
        Given the clinician creates an epr encounter
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the clinician creates a child encounter of encounter 1
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the clinician deletes encounter 2
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And an AUDIT_MESSAGE message is published to RabbitMQ
        When the clinician searches for latest encounter by patient uuid
        Then the search result returns encounter 1

    Scenario: Latest encounter for patient with multiple epr encounters where some are closed/deleted
        Given the clinician creates an epr encounter
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the clinician creates another epr encounter
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the clinician creates another epr encounter
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        When the clinician searches for latest encounter by patient uuid
        Then the search result returns encounter 3
        When the clinician deletes encounter 3
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And an AUDIT_MESSAGE message is published to RabbitMQ
        And the clinician searches for latest encounter by patient uuid
        Then the search result returns encounter 2
        When the clinician closes encounter 2
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And an AUDIT_MESSAGE message is published to RabbitMQ
        And the clinician searches for latest encounter by patient uuid
        Then the search result returns encounter 1
        And the clinician can see that the patient has 2 encounters
