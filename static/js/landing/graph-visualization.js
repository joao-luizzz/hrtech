// D3.js force-directed graph visualization
// Renders skill graphs on HTML5 canvas for 60fps performance

import {
  heroGraphData,
  mobileGraphData,
  howItWorksGraphData,
  nodeColors
} from './graph-config.js';

// Utility function: debounce
function debounce(fn, delay) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), delay);
  };
}

// Get color for node based on group
function getNodeColor(group) {
  return nodeColors[group] || '#0066FF';
}

// Initialize hero graph visualization
export function initializeHeroGraph() {
  const canvas = document.getElementById('hero-graph-canvas');
  if (!canvas) return; // Graceful degradation if canvas missing

  const width = canvas.clientWidth || window.innerWidth;
  const height = canvas.clientHeight || 600;
  const context = canvas.getContext('2d');

  if (!context) return; // Fail silently if canvas context unavailable

  // Detect mobile
  const isMobile = window.innerWidth < 768;
  const data = isMobile ? mobileGraphData : heroGraphData;

  // Canvas pixel ratio for retina displays
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = width * pixelRatio;
  canvas.height = height * pixelRatio;
  context.scale(pixelRatio, pixelRatio);

  // Force simulation
  const simulation = d3.forceSimulation(data.nodes)
    .force('link', d3.forceLink(data.links)
      .id(d => d.id)
      .distance(d => d.distance || 80))
    .force('charge', d3.forceManyBody()
      .strength(isMobile ? -150 : -300))
    .force('collide', isMobile ? null : d3.forceCollide().radius(35))
    .force('center', d3.forceCenter(width / 2, height / 2));

  // Render loop
  simulation.on('tick', () => {
    // Clear canvas with slight trail effect
    context.fillStyle = 'rgba(15, 20, 25, 0.05)';
    context.fillRect(0, 0, width, height);

    // Draw links
    context.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    context.lineWidth = 2;
    data.links.forEach(link => {
      context.beginPath();
      context.moveTo(link.source.x, link.source.y);
      context.lineTo(link.target.x, link.target.y);
      context.stroke();
    });

    // Draw nodes
    data.nodes.forEach(node => {
      context.beginPath();
      context.arc(node.x, node.y, 15, 0, 2 * Math.PI);
      const color = getNodeColor(node.group);
      context.fillStyle = color;
      context.fill();
      context.strokeStyle = '#FFFFFF';
      context.lineWidth = 2;
      context.stroke();
    });
  });

  // Handle window resize
  window.addEventListener('resize', debounce(() => {
    const newWidth = canvas.clientWidth;
    const newHeight = canvas.clientHeight;
    canvas.width = newWidth * pixelRatio;
    canvas.height = newHeight * pixelRatio;
    context.scale(pixelRatio, pixelRatio);
    simulation.force('center', d3.forceCenter(newWidth / 2, newHeight / 2));
  }, 300));

  return simulation;
}

// Initialize how-it-works graph visualization
export function initializeHowItWorksGraph() {
  const canvas = document.getElementById('how-it-works-graph-canvas');
  if (!canvas) return;

  const width = canvas.clientWidth || 400;
  const height = 400;
  const context = canvas.getContext('2d');

  if (!context) return;

  // Canvas pixel ratio
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = width * pixelRatio;
  canvas.height = height * pixelRatio;
  context.scale(pixelRatio, pixelRatio);

  // Force simulation for how-it-works graph
  const simulation = d3.forceSimulation(howItWorksGraphData.nodes)
    .force('link', d3.forceLink(howItWorksGraphData.links)
      .id(d => d.id)
      .distance(60))
    .force('charge', d3.forceManyBody()
      .strength(-100))
    .force('center', d3.forceCenter(width / 2, height / 2));

  // Render loop
  simulation.on('tick', () => {
    // Clear canvas
    context.fillStyle = 'rgba(15, 20, 25, 1)';
    context.fillRect(0, 0, width, height);

    // Draw links
    context.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    context.lineWidth = 2;
    howItWorksGraphData.links.forEach(link => {
      context.beginPath();
      context.moveTo(link.source.x, link.source.y);
      context.lineTo(link.target.x, link.target.y);
      context.stroke();
    });

    // Draw nodes
    howItWorksGraphData.nodes.forEach(node => {
      context.beginPath();
      context.arc(node.x, node.y, 12, 0, 2 * Math.PI);
      const color = getNodeColor(node.group);
      context.fillStyle = color;
      context.fill();
      context.strokeStyle = '#FFFFFF';
      context.lineWidth = 2;
      context.stroke();
    });
  });

  // Handle resize
  window.addEventListener('resize', debounce(() => {
    const newWidth = canvas.clientWidth;
    canvas.width = newWidth * pixelRatio;
    canvas.height = height * pixelRatio;
    context.scale(pixelRatio, pixelRatio);
    simulation.force('center', d3.forceCenter(newWidth / 2, height / 2));
  }, 300));

  return simulation;
}
