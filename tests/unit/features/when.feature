Feature: Reusable `when` steps
  Background:
    Given I add model 'test'

  Scenario: Run action on one unit
    When I run action 'get-password' on unit 'slurmctld/0'

  Scenario: Run action on multiple units with params in model
    When I run action 'set-config' on units 'slurmctld/0', 'slurmctld/1', and 'slurmctld/2' with parameters 'debug=true key=val' in model 'test'

  Scenario: Exec command on one machine
    When I execute 'hostname' on machine '0'

  Scenario: Exec command on multiple units in model
    When I execute 'systemctl restart slurmd' on units 'slurmd/0', 'slurmd/1', and 'slurmd/2' in model 'test'
