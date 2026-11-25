Feature: Reusable `when` steps
  Background:
    Given I add model 'test'

  Scenario: Run action on one unit
    When I run action 'get-password' on unit 'slurmctld/0'

  Scenario: Run action on two units without comma
    When I run action 'get-password' on units 'slurmctld/0' and 'slurmctld/1'

  Scenario: Run action on multiple units with params in model
    When I run action 'set-config' on units 'slurmctld/0', 'slurmctld/1', and 'slurmctld/2' with parameters 'debug=true key=val' in model 'test' and it completes within '45' seconds

  Scenario: Run failing action on one unit
    When I run action 'failing-action' on unit 'slurmctld/0'

  Scenario: Exec command on one machine
    When I execute 'hostname' on machine '0'

  Scenario: Exec command on multiple units in model
    When I execute 'systemctl restart slurmd' on units 'slurmd/0', 'slurmd/1', and 'slurmd/2' in model 'test' within '45' seconds

  Scenario: Exec failing command on one machine
    When I execute 'exit 2' on machine '0'

  Scenario: Exec command on machine as user in model
    When I execute 'cat /etc/shadow' on machine '0' as user 'nobody' in model 'test' within '45' seconds

  Scenario: SSH into machine and execute command
    When I ssh into machine '0' and I execute 'hostname'

  Scenario: SSH into machine and execute command within timeout
    When I ssh into machine '0' and I execute 'hostname' within '30' seconds

  Scenario: SSH into unit and execute command
    When I ssh into unit 'slurmctld/0' and I execute 'hostname'

  Scenario: SSH into unit and execute command in model
    When I ssh into unit 'slurmctld/0' and I execute 'hostname' as user 'nobody' in model 'test' and it completes within '45' seconds using identity file '/home/ubuntu/.ssh/juju_id_ed25519'

  Scenario: Copy file to unit
    When I copy '/tmp/sbatch_sleep_job.sh' to unit 'login/0'

  Scenario: Copy file to unit at remote path in model
    When I copy '/tmp/sbatch_sleep_job.sh' to unit 'login/0' at '/home/ubuntu/sbatch_sleep_job.sh' in model 'test' using private key file '/home/ubuntu/.ssh/juju_id_ed25519'

  Scenario: Copy file from unit
    When I copy '/home/ubuntu/sbatch_sleep_job.sh' from unit 'login/0'

  Scenario: Copy file from unit to local path in model
    When I copy '/home/ubuntu/sbatch_sleep_job.sh' from unit 'login/0' to 'testdata/sbatch_sleep_job.sh' in model 'test' and use identity file '/home/ubuntu/.ssh/juju_id_ed25519'

  Scenario: Copy directory to unit
    When I copy '/tmp/reframe_benchmarks' to unit 'login/0'

  Scenario: Copy directory from unit
    When I copy '/home/ubuntu/reframe_benchmarks' from unit 'login/0'

  Scenario: Copy file to machine
    When I copy '/tmp/sbatch_sleep_job.sh' to machine '0'

  Scenario: Copy file from machine
    When I copy '/home/ubuntu/sbatch_sleep_job.sh' from machine '0'
