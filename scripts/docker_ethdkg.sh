#!/bin/bash

docker run \
  --mount type=bind,source=$(pwd),target=/ethdkg \
  --net="host" \
  --user 1000 \
  -it ethdkg:latest /bin/bash
