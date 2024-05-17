# CS 145 Project 2

## Author and collaborators

### Author name

Cory Zimmerman, cfzimmerman@college.harvard.edu

### Collaborators

Office hours

## Report

## Citations

## Grading notes (if any)

## Extra credit attempted (if any)

I did both DVrouter and LSrouter. DVrouter should definitely be correct, so
I'd prefer that for my base grade.

LSrouter occasionally fails test four. Based on logging, I think it might
be because out of order packets are dropped. For example, consider this scenario:

- Router A currently says its last packet from E has id 4
- Router A receives a packet from E with id 6. It updates its last id from E to 6.
- Router A receives a (delayed) packet from E with id 5. That update is ignored.

If the ignored update is related to a link failure, essential information is lost
and not recovered until the next heartbeat. I think test 4 fails when this packet
ignoring occurs but the test ends before the necessary heartbeat.
Anyway, I unfortunately don't have more time to debug it. If LS test 4 fails
during grading, I'm hoping you'd at least consider some partial extra credit.
Thanks!
