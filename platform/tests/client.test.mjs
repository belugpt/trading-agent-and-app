import {test} from 'node:test';import assert from 'node:assert/strict';import vm from 'node:vm';import {readFileSync} from 'node:fs';
const html=readFileSync('web/index.html','utf8'),script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
test('client script parses',()=>assert.ok(new vm.Script(script)));
test('every navigation page and critical control exists',()=>{for(const id of ['overview','setups','risk','journal','research','connect','spec','size-form','journal-form','refresh','research-table','event-kind'])assert.ok(html.includes('id="'+id+'"'),id);});
test('CSV export neutralizes spreadsheet formulas and preserves numeric losses',()=>{const fn=script.match(/function csvCell\(v\)\{[^\n]+/)[0];const cell=vm.runInNewContext(fn+';csvCell');assert.equal(cell('=2+2'),'"\'=2+2"');assert.equal(cell(-10),'"-10"');assert.equal(cell('a"b'),'"a""b"');});
