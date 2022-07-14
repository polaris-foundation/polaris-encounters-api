Feature: Encounter management
    As a clinician
    I want to manage encounters
    So that I can record patients' visits accordingly

    Background:
        Given a valid system JWT
        And RabbitMQ is running
        And there exists a patient
       
    Scenario: Clinician creates a new encounter
        When the clinician creates a local encounter
        Then an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the message contained the encounter uuid
        And the clinician can retrieve the encounter by its uuid
        And the retrieved encounter body matches that used to create it

    Scenario: Patient can't have multiple open local encounters
        Given the patient has a local encounter
        When the clinician tries to create a local encounter
        Then the attempt fails
        And the clinician can see that the patient has 1 encounter

    Scenario: Patient has closed and open encounters
        Given the patient has a local encounter
        And the clinician closes the encounter
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the message contained the encounter uuid
        And an AUDIT_MESSAGE message is published to RabbitMQ
        When the clinician creates a local encounter
        Then an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the message contained the encounter uuid
        And the clinician can see that the patient has 2 encounters

    Scenario: EPR encounters can have nested child encounters
        Given the clinician creates an epr encounter
        And an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the message contained the encounter uuid
        When the clinician creates a child encounter of encounter 1
        Then an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the message contained the encounter uuid
        And the clinician can see that the patient has 2 encounters
        When the clinician creates a child encounter of encounter 2
        Then an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And the message contained the encounter uuid
        And the clinician can see that the patient has 3 encounters

    Scenario: Encounter merge
        Given the patient has a local encounter
        When the encounter details are merged with those of another encounter
        And the encounter is retrieved by its uuid
        Then the retrieved encounter details match that of the merge parent

    Scenario: Encounter delete
        Given the patient has a local encounter
        When the clinician deletes the encounter
        Then an ENCOUNTER_UPDATED_MESSAGE message is published to RabbitMQ
        And an AUDIT_MESSAGE message is published to RabbitMQ
        And the encounter can not be retrieved by its uuid
        But the clinician can retrieve the encounter by its uuid if deleted encounters are included
