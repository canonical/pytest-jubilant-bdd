Feature: Reusable `then` steps
  Background:
    Given I add model 'test'

  Scenario: All agents are idle
    Then all agents are 'idle'

  Scenario: All agents idle in multiple models
    Given I add model 'compute'
    Given I add model 'gpu'
    Then all agents are 'idle' in models 'test', 'compute', and 'gpu'

  Scenario: All agents idle in two models without comma
    Given I add model 'sssd'
    Given I add model 'ldap'
    Then all agents are 'idle' in models 'sssd' and 'ldap'

  Scenario: All agents idle with all optionals
    Given I add model 'compute'
    Then all agents are 'idle' in models 'test', 'compute' within '90' seconds

  Scenario: Workload status for app
    Then the workload status for app 'slurmctld' is 'active'

  Scenario: Workload status for unit
    Then the workload status for unit 'slurmctld/0' is 'active'

  Scenario: Workload status for app with all optionals
    Then the workload status for app 'slurmctld' is 'active' within '90' seconds

  Scenario: Workload status for unit with all optionals
    Then the workload status for unit 'slurmctld/0' is 'active' within '90' seconds

  Scenario: Workload status message for app
    Then the workload status message for app 'slurmctld' is 'ready'

  Scenario: Workload status message for unit
    Then the workload status message for unit 'slurmctld/0' is 'installing agent'

  Scenario: Workload status message for app with all optionals
    Then the workload status message for app 'slurmctld' is 'ready' within '90' seconds

  Scenario: Workload status message for unit with all optionals
    Then the workload status message for unit 'slurmctld/0' is 'installing agent' within '90' seconds

  Scenario: Storage instances are attached
    Then '3' instances of storage 'ost' are attached to unit 'lustre-server/1'

  Scenario: Storage instances are attached with all optionals
    Then '3' instances of storage 'ost' are attached to unit 'lustre-server/1' in model 'test' within '90' seconds
