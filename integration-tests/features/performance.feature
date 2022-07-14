Feature: Performance
  As a SEND clinician
  I want the patient list to load quickly
  So that I have a pleasant experience using the product

  Background:
    Given a valid system JWT

  Scenario: Retrieve many encounters by many locations
    Given there exist 5k encounters at 2k different locations
    When timing this step
     And we retrieve the encounters at all of the locations
    Then it took less than 2 seconds to complete
     And we received all of the expected encounters
