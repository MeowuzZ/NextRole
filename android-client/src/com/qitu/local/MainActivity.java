package com.qitu.local;

import android.app.*;
import android.content.*;
import android.database.Cursor;
import android.database.sqlite.*;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.print.PrintAttributes;
import android.print.PrintManager;
import android.webkit.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Offline client: bundled UI + native private SQLite, no Internet permission. */
public final class MainActivity extends Activity {
 private static final String HOST="appassets.androidplatform.net";
 private static final String START="https://"+HOST+"/assets/index.html";
 private static final int PICK=100,EXPORT=101;
 private WebView web; private Store store; private ValueCallback<Uri[]> fileCallback;
 private byte[] pendingExport;
 @Override public void onCreate(Bundle state){super.onCreate(state);
  // Keep the WebView viewport inside system bars; adjustResize handles the IME.
  if(android.os.Build.VERSION.SDK_INT>=30)getWindow().setDecorFitsSystemWindows(true);
  getWindow().setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
  store=new Store(this);web=new WebView(this);web.setBackgroundColor(Color.rgb(243,246,252));setContentView(web);
  WebSettings settings=web.getSettings();settings.setJavaScriptEnabled(true);settings.setDomStorageEnabled(true);settings.setDatabaseEnabled(true);settings.setAllowFileAccess(false);settings.setAllowContentAccess(true);settings.setAllowFileAccessFromFileURLs(false);settings.setAllowUniversalAccessFromFileURLs(false);settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);settings.setSupportMultipleWindows(false);settings.setMediaPlaybackRequiresUserGesture(true);settings.setTextZoom(100);
  web.addJavascriptInterface(new Bridge(),"QituNative");
  web.setWebViewClient(new WebViewClient(){
   @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request){if(isLocal(request.getUrl()))return false;Toast.makeText(MainActivity.this,"离线客户端不打开外部网页",Toast.LENGTH_SHORT).show();return true;}
   @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request){Uri uri=request.getUrl();if(!isLocal(uri))return rejected();String path=uri.getPath();if(path==null||!path.startsWith("/assets/"))return rejected();String asset=path.substring(8);if(asset.contains("..")||!asset.matches("[a-zA-Z0-9_./-]+"))return rejected();try{String mime=asset.endsWith(".html")?"text/html":asset.endsWith(".js")?"text/javascript":asset.endsWith(".css")?"text/css":asset.endsWith(".json")?"application/json":"application/octet-stream";WebResourceResponse response=new WebResourceResponse(mime,"UTF-8",getAssets().open("www/"+asset));Map<String,String> headers=new HashMap<>();headers.put("Cache-Control","no-store");headers.put("X-Content-Type-Options","nosniff");response.setResponseHeaders(headers);return response;}catch(IOException e){return rejected();}}
  });
  web.setWebChromeClient(new WebChromeClient(){
   @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params){if(fileCallback!=null)fileCallback.onReceiveValue(null);fileCallback=callback;Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT);intent.addCategory(Intent.CATEGORY_OPENABLE);intent.setType("*/*");String[] accepts=params.getAcceptTypes();if(accepts.length>0&&accepts[0].startsWith("image/"))intent.setType("image/*");try{startActivityForResult(intent,PICK);}catch(ActivityNotFoundException e){fileCallback.onReceiveValue(null);fileCallback=null;Toast.makeText(MainActivity.this,"系统文件选择器不可用",Toast.LENGTH_LONG).show();}return true;}
  });
  android.content.pm.PackageInfo provider=WebView.getCurrentWebViewPackage();
  if(provider!=null){try{int major=Integer.parseInt(provider.versionName.split("\\.")[0]);if(major<110){new AlertDialog.Builder(this).setTitle("需要更新系统 WebView").setMessage("请将 Android System WebView 更新到 110 或以上，以使用本地表单与弹窗。").setPositiveButton("知道了",(d,w)->web.loadUrl(START)).show();return;}}catch(NumberFormatException ignored){}}
  web.loadUrl(START);
 }
 private boolean isLocal(Uri uri){return "https".equals(uri.getScheme())&&HOST.equals(uri.getHost())&&uri.getPort()==-1;}
 private WebResourceResponse rejected(){return new WebResourceResponse("text/plain","UTF-8",403,"Blocked",Collections.emptyMap(),new ByteArrayInputStream("Offline only".getBytes(StandardCharsets.UTF_8)));}
 public final class Bridge {
  @JavascriptInterface public String readState(){return store.read();}
  @JavascriptInterface public boolean writeState(int revision,String value){return value!=null&&value.length()<=64*1024*1024&&store.write(revision,value);}
  @JavascriptInterface public void exportText(String name,String mime,String content){if(content==null||content.length()>32*1024*1024)return;runOnUiThread(()->{if(pendingExport!=null){Toast.makeText(MainActivity.this,"请先完成当前文件导出",Toast.LENGTH_SHORT).show();return;}pendingExport=content.getBytes(StandardCharsets.UTF_8);Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);intent.addCategory(Intent.CATEGORY_OPENABLE);intent.setType("text/csv".equals(mime)?"text/csv":"application/json");intent.putExtra(Intent.EXTRA_TITLE,name==null?"NextRole备份.json":name.replaceAll("[/\\\\]","_"));try{startActivityForResult(intent,EXPORT);}catch(ActivityNotFoundException e){pendingExport=null;Toast.makeText(MainActivity.this,"系统文件保存器不可用",Toast.LENGTH_LONG).show();}});}
  @JavascriptInterface public void printPage(){runOnUiThread(()->{PrintManager manager=(PrintManager)getSystemService(PRINT_SERVICE);if(manager!=null)manager.print("NextRole简历",web.createPrintDocumentAdapter("NextRole简历"),new PrintAttributes.Builder().build());});}
 }
 private static final class Store extends SQLiteOpenHelper {
  Store(Context context){super(context,"qitu-private.db",null,1);}
  @Override public void onCreate(SQLiteDatabase db){db.execSQL("CREATE TABLE workspace(id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, body TEXT NOT NULL)");db.execSQL("INSERT INTO workspace VALUES(1,0,'{\"records\":[]}')");}
  @Override public void onUpgrade(SQLiteDatabase db,int oldVersion,int newVersion){}
  synchronized String read(){try(Cursor cursor=getReadableDatabase().rawQuery("SELECT revision,body FROM workspace WHERE id=1",null)){if(cursor.moveToFirst()){JSONObject result=new JSONObject();result.put("revision",cursor.getInt(0));result.put("data",new JSONObject(cursor.getString(1)));return result.toString();}}catch(Exception ignored){}return "{\"revision\":0,\"data\":{\"records\":[]}}";}
  synchronized boolean write(int expected,String body){SQLiteDatabase db=getWritableDatabase();db.beginTransaction();try{JSONObject parsed=new JSONObject(body);if(!parsed.has("records")||!(parsed.get("records") instanceof JSONArray))return false;ContentValues values=new ContentValues();values.put("revision",expected+1);values.put("body",body);int count=db.update("workspace",values,"id=1 AND revision=?",new String[]{Integer.toString(expected)});if(count!=1)return false;db.setTransactionSuccessful();return true;}catch(Exception ignored){return false;}finally{db.endTransaction();}}
 }
 @Override protected void onActivityResult(int request,int result,Intent data){super.onActivityResult(request,result,data);if(request==PICK){if(fileCallback!=null){fileCallback.onReceiveValue(result==RESULT_OK&&data!=null&&data.getData()!=null?new Uri[]{data.getData()}:null);fileCallback=null;}}else if(request==EXPORT){final byte[] bytes=pendingExport;pendingExport=null;if(result==RESULT_OK&&data!=null&&data.getData()!=null&&bytes!=null){final Uri uri=data.getData();new Thread(()->{try(OutputStream out=getContentResolver().openOutputStream(uri)){if(out==null)throw new IOException();out.write(bytes);runOnUiThread(()->Toast.makeText(this,"文件已保存",Toast.LENGTH_SHORT).show());}catch(IOException e){runOnUiThread(()->Toast.makeText(this,"保存失败，请重试",Toast.LENGTH_LONG).show());}}).start();}}}
 @Override public void onBackPressed(){web.evaluateJavascript("(function(){var picker=document.querySelector('.choice-picker[open]');if(picker){picker.querySelector('.choice-close').click();return true}var m=document.querySelector('#modal');if(m&&m.open){m.querySelector('.dialog-close').click();return true}var d=document.querySelector('#record-drawer');if(d&&d.open){d.querySelector('#close-record').click();return true}var b=document.querySelector('#back-resume');if(b){b.click();return true}if(location.hash!=='#board'){document.querySelector('[data-nav=board]').click();return true}return false})()",result->{if(!"true".equals(result))new AlertDialog.Builder(this).setTitle("退出NextRole？").setMessage("已保存的资料保留在手机本地。").setNegativeButton("取消",null).setPositiveButton("退出",(dialog,which)->finish()).show();});}
 @Override protected void onPause(){web.onPause();super.onPause();}
 @Override protected void onResume(){super.onResume();if(web!=null)web.onResume();}
 @Override protected void onDestroy(){if(fileCallback!=null)fileCallback.onReceiveValue(null);web.removeJavascriptInterface("QituNative");web.destroy();store.close();super.onDestroy();}
}
