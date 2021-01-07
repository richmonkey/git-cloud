var React = require('react');
var ReactDOM = require('react-dom');

import {Root} from "./root";

var root;
ReactDOM.render(
    <Root ref={a => root=a}/>,
    document.getElementById('root')
);

function updateRepoState(repoName, lastSyncTime, syncing, syncResult) {
    root.updateRepoState(repoName, lastSyncTime, syncing, syncResult);
}
window.updateRepoState = updateRepoState;