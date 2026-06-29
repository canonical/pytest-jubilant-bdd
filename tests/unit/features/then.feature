Feature: Reusable `then` steps
  Background:
    Given I add model 'test'

  Scenario: All agents are idle
    Then all agents are 'idle'

  Scenario: All agents idle in multiple models
    Given I add model 'compute'
    Given I add model 'gpu'
    Then all agents are 'idle' in models 'test', 'compute', and 'gpu'

  Scenario: Workload status for app
    Then the workload status for app 'slurmctld' is 'active'

  Scenario: Workload status for unit
    Then the workload status for unit 'slurmctld/0' is 'active'

  Scenario: Workload status message for app
    Then the workload status message for app 'slurmctld' is 'ready'

  Scenario: Workload status message for unit
    Then the workload status message for unit 'slurmctld/0' is 'installing agent'
