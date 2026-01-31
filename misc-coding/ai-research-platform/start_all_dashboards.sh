#!/bin/bash
set -e

# Bring down all dashboards first to avoid port conflicts
echo "Stopping all dashboards..."
(cd sub-projects/idea-database && docker-compose down)
echo "Idea Database dashboard stopped."
(cd sub-projects/twin-report-kb/docker/frontend && docker-compose down)
echo "Twin Report KB dashboard stopped."

echo "\nStarting all dashboards..."
(cd sub-projects/idea-database && docker-compose up -d web_interface)
echo "Idea Database dashboard started at http://localhost:3002"
(cd sub-projects/twin-report-kb/docker/frontend && docker-compose up -d web_interface)
echo "Twin Report KB dashboard started at http://localhost:3100 (or as defined)"

echo "\nAll dashboards are up!" 