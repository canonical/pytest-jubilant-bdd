Feature: Reusable `when` steps
  Background:
    Given I add model 'test'

  Scenario: Run action on one unit
    When I run action 'get-password' on unit 'slurmctld/0'

  Scenario: Run action on two units without comma
    When I run action 'get-password' on units 'slurmctld/0' and 'slurmctld/1'

  Scenario: Run action on multiple units with params in model
    When I run action 'set-config' on units 'slurmctld/0', 'slurmctld/1', and 'slurmctld/2' with parameters 'debug=true key=val' in model 'test'

  Scenario: Run failing action on one unit
    When I run action 'failing-action' on unit 'slurmctld/0'

  Scenario: Exec command on one machine
    When I execute 'hostname' on machine '0'

  Scenario: Exec command on two units without comma
    When I execute 'hostname' on units 'slurmd/0' and 'slurmd/1'

  Scenario: Exec command on multiple units in model
    When I execute 'systemctl restart slurmd' on units 'slurmd/0', 'slurmd/1', and 'slurmd/2' in model 'test'

  Scenario: Exec failing command on one machine
    When I execute 'exit 2' on machine '0'

  Scenario: SSH into machine and execute command
    When I ssh into machine '0' and I execute 'hostname'

  Scenario: SSH into unit and execute command
    When I ssh into unit 'slurmctld/0' and I execute 'hostname'

  Scenario: SSH into unit and execute command in model
    When I ssh into unit 'slurmctld/0' and I execute 'hostname' in model 'test'
