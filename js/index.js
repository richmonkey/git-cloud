var React = require('react');
var ReactDOM = require('react-dom');

import {Root} from "./root";

var root;
ReactDOM.render(
    <Root ref={a => root=a}/>,
    document.getElementById('root')
);

function updateRepoState(repoName, lastSyncTime, syncing) {
    root.updateRepoState(repoName, lastSyncTime, syncing);
}
window.updateRepoState = updateRepoState;