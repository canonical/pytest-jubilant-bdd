Feature: Reusable `given` steps
  Scenario: Add model
    Given I add model 'test'

  Scenario: Deploy
    Given I deploy 'slurmctld'

  Scenario: Deploy with all optionals
    Given I add model 'test'
    Given I deploy 'slurmctld' in model 'test' from channel 'latest/edge' on base 'ubuntu@24.04' with '3' units

  Scenario: Deploy local
    Given I add model 'test'
    Given I deploy 'slurmctld' from a local charm

  Scenario: Deploy local with all optionals
    Given I add model 'test'
    Given I deploy 'slurmctld' from a local charm located at '/tmp/fake.charm' in model 'test' on base 'ubuntu@24.04' with '3' units

  Scenario: Integrate
    Given I integrate 'slurmctld' with 'slurmd'

  Scenario: Model exists
    Given I add model 'test'
    Given model 'test' exists

  Scenario: Is integrated
    Given I add model 'test'
    Given 'slurmctld' is integrated with 'slurmd'

  Scenario: Is deployed
    Given I add model 'test'
    Given 'slurmctld' is deployed

  Scenario: Is deployed in model
    Given I add model 'test'
    Given 'slurmctld' is deployed in model 'test'

  Scenario: Add unit
    Given I add '3' units to app 'slurmctld'

  Scenario: Add unit in model
    Given I add model 'test'
    Given I add '2' units to app 'slurmctld' in model 'test'

  Scenario: Set app config
    Given I add model 'test'
    Given I deploy 'slurmctld'
    Given I set 'debug' for app 'slurmctld' to 'true'

  Scenario: Set app config in model
    Given I add model 'test2'
    Given I deploy 'slurmctld' in model 'test2'
    Given I set 'debug' for app 'slurmctld' to 'true' in model 'test2'
