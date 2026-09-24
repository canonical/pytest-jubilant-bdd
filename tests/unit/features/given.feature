Feature: Reusable `given` steps
  Scenario: Add model
    Given I add model 'test'

  Scenario: Pack charm
    Given I pack a 'my-charm' charm

  Scenario: Pack charm from project directory
    Given I pack a 'my-charm' charm from project directory '/path/to/project'

  Scenario: Deploy
    Given I deploy 'slurmctld'

  Scenario: Deploy with all optionals
    Given I add model 'test'
    Given I deploy 'slurmctld' in model 'test' from channel 'latest/edge' on base 'ubuntu@24.04' with '3' units with name 'controller' with constraints 'virt-type=virtual-machine cores=4 mem=5G'

  Scenario: Deploy local
    Given I add model 'test'
    Given I deploy 'slurmctld' from a local charm

  Scenario: Deploy local with all optionals
    Given I add model 'test'
    Given I deploy 'slurmctld' from a local charm located at '/tmp/fake.charm' in model 'test' on base 'ubuntu@24.04' with '3' units with name 'controller' with constraints 'virt-type=virtual-machine cores=4 mem=5G'

  Scenario: Create offer
    Given I create offer 'mysql-offer' from app 'mysql' and endpoint 'db'

  Scenario: Create offer with all optionals
    Given I add model 'test'
    Given I create offer 'mysql-offer' from app 'mysql' and endpoint 'db' in model 'test'

  Scenario: Consume offer
    Given I consume offer 'othermodel.mysql'

  Scenario: Consume offer with all optionals
    Given I add model 'test'
    Given I consume offer 'othermodel.mysql' as 'sql' in model 'test'

  Scenario: Integrate
    Given I integrate 'slurmctld' with 'slurmd'

  Scenario: Integrate in model
    Given I add model 'test'
    Given I integrate 'slurmctld' with 'slurmd' in model 'test'

  Scenario: Disintegrate
    Given I disintegrate 'slurmctld' and 'slurmd'

  Scenario: Disintegrate in model
    Given I add model 'test'
    Given I disintegrate 'slurmctld' and 'slurmd' in model 'test'

  Scenario: Model exists
    Given I add model 'test'
    Given model 'test' exists

  Scenario: Is integrated
    Given I add model 'test'
    Given 'slurmctld' is integrated with 'slurmd'

  Scenario: Is integrated in model
    Given I add model 'test'
    Given 'slurmctld' is integrated with 'slurmd' in model 'test'

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

  Scenario: Add machine
    Given I add a machine

  Scenario: Add machine with all optionals
    Given I add model 'test'
    Given I add '2' machines to 'lxd:25' in model 'test' that use base 'ubuntu@24.04' with constraints 'mem=8G cores=4' and with disks 'ebs,1T,2'

  Scenario: Add storage
    Given I add storage 'ost' to unit 'lustre-server/1'

  Scenario: Add storage with all optionals
    Given I add model 'test'
    Given I add storage 'ost' to unit 'lustre-server/1' from pool 'loop' of size '1G' with '3' instances in model 'test'

  Scenario: Remove unit
    Given I remove unit 'slurmctld/0'

  Scenario: Remove unit in model
    Given I add model 'test'
    And I remove units 'slurmctld/0', 'slurmctld/1', and 'slurmctld/2' in model 'test'

  Scenario: Remove storage
    Given I remove storage 'ost/0'

  Scenario: Remove storage in model
    Given I add model 'test'
    And I remove storage 'ost/0', 'ost/1', and 'ost/2' in model 'test'

  Scenario: Set app config
    Given I add model 'test'
    Given I deploy 'slurmctld'
    Given I set 'debug' for app 'slurmctld' to 'true'

  Scenario: Set app config in model
    Given I add model 'test2'
    Given I deploy 'slurmctld' in model 'test2'
    Given I set 'debug' for app 'slurmctld' to 'true' in model 'test2'

  Scenario: App config is set
    Given I add model 'test'
    And I deploy 'slurmctld'
    And 'debug' for app 'slurmctld' is set to 'true'

  Scenario: App config is set in model
    Given I add model 'test2'
    And I deploy 'slurmctld' in model 'test2'
    And 'debug' for app 'slurmctld' is set to 'true' in model 'test2'

  Scenario: Set model config
    Given I add model 'test'
    Given I set 'update-status-hook-interval' for model 'test' to '10s'

  Scenario: Reset model config
    Given I add model 'test'
    Given I reset 'update-status-hook-interval' for model 'test'

  Scenario: Reset app config
    Given I add model 'test'
    Given I deploy 'slurmctld'
    Given I reset 'debug' for app 'slurmctld'

  Scenario: Reset app config in model
    Given I add model 'test2'
    Given I deploy 'slurmctld' in model 'test2'
    Given I reset 'debug' for app 'slurmctld' in model 'test2'

  Scenario: Switch model
    Given I add model 'test'
    Given I switch to model 'test'
